from fastapi import APIRouter, HTTPException, Query
from models.cassandra import SensorReading, SensorReadingResponse, MetricStats, SensorSummary
import asyncio
from db.cassandra import get_session
from typing import Optional, Union
from datetime import datetime, timedelta, timezone
import zlib
from db.redis import get_client

router = APIRouter(prefix="/sensors")

NUM_SHARDS = 4
def get_bucket_start(reading_time): return reading_time.astimezone(timezone.utc).replace(second=0, microsecond=0)
def get_shard(sensor_id): return zlib.crc32(sensor_id.encode()) % NUM_SHARDS


@router.post("/readings", response_model=SensorReadingResponse, status_code=201)
async def ingest_reading(payload: Union[SensorReading, list[SensorReading]]):
    readings = payload if isinstance(payload, list) else [payload]
    if not readings: raise HTTPException(status_code=400, detail="Reading batch cannot be empty")

    session = get_session()

    query = """
        INSERT INTO sensor_readings (
            sensor_id,
            reading_time,
            metric_type,
            value,
            unit,
            quality_flag
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """

    bucket_query = """
        INSERT INTO sensor_readings_by_bucket (
            bucket_start,
            shard,
            reading_time,
            sensor_id,
            metric_type,
            value,
            unit,
            quality_flag
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    prepared = session.prepare(query)
    bucket_prepared = session.prepare(bucket_query)

    for reading in readings:
        await asyncio.to_thread(
            session.execute,
            prepared,
            (
                reading.sensor_id,
                reading.reading_time,
                reading.metric_type,
                reading.value,
                reading.unit,
                reading.quality_flag,
            ),
        )

        bucket_start = get_bucket_start(reading.reading_time)
        shard = get_shard(reading.sensor_id)

        await asyncio.to_thread(
            session.execute,
            bucket_prepared,
            (
                bucket_start,
                shard,
                reading.reading_time,
                reading.sensor_id,
                reading.metric_type,
                reading.value,
                reading.unit,
                reading.quality_flag,
            ),
        )

    return {
        "message": f"Ingested values ({len(readings)})"
    }

@router.get("/{sensor_id}/readings", response_model=list[SensorReading])
async def get_readings(
    sensor_id: str,
    limit: int = Query(100, ge=1, le=10000),
    from_time: Optional[datetime] = None,
):
    session = get_session()

    if from_time is not None:
        query = """
            SELECT sensor_id,
                   reading_time,
                   metric_type,
                   value,
                   unit,
                   quality_flag
            FROM sensor_readings
            WHERE sensor_id = ?
              AND reading_time >= ?
            LIMIT ?
        """

        parameters = (
            sensor_id,
            from_time,
            limit,
        )

    else:
        query = """
            SELECT sensor_id,
                   reading_time,
                   metric_type,
                   value,
                   unit,
                   quality_flag
            FROM sensor_readings
            WHERE sensor_id = ?
            LIMIT ?
        """

        parameters = (
            sensor_id,
            limit,
        )

    prepared = session.prepare(query)

    rows = await asyncio.to_thread(
        session.execute,
        prepared,
        parameters,
    )

    return [
        SensorReading(
            sensor_id=row.sensor_id,
            reading_time=row.reading_time,
            metric_type=row.metric_type,
            value=row.value,
            unit=row.unit,
            quality_flag=row.quality_flag,
        )
        for row in rows
    ]

@router.get("/{sensor_id}/summary", response_model=SensorSummary)
async def get_summary(sensor_id: str):
    redis_client = get_client()
    cache_key = f"sensor_summary:{sensor_id}"

    cached = await redis_client.get(cache_key)

    if cached is not None:
        return SensorSummary.model_validate_json(cached)

    session = get_session()

    latest_query = """
        SELECT sensor_id,
               reading_time,
               metric_type,
               value,
               unit,
               quality_flag
        FROM sensor_readings
        WHERE sensor_id = ?
        LIMIT 1
    """

    since = datetime.now(timezone.utc) - timedelta(hours=1)

    window_query = """
        SELECT sensor_id,
               reading_time,
               metric_type,
               value,
               unit,
               quality_flag
        FROM sensor_readings
        WHERE sensor_id = ?
          AND reading_time >= ?
    """

    latest_prepared = session.prepare(latest_query)
    window_prepared = session.prepare(window_query)

    latest_row = await asyncio.to_thread(
        lambda: session.execute(
            latest_prepared,
            (sensor_id,),
        ).one()
    )

    rows = await asyncio.to_thread(
        lambda: list(
            session.execute(
                window_prepared,
                (sensor_id, since),
            )
        )
    )

    latest = None

    if latest_row is not None:
        latest = SensorReading(
            sensor_id=latest_row.sensor_id,
            reading_time=latest_row.reading_time,
            metric_type=latest_row.metric_type,
            value=latest_row.value,
            unit=latest_row.unit,
            quality_flag=latest_row.quality_flag,
        )

    grouped = {}

    for row in rows:
        if row.metric_type not in grouped:
            grouped[row.metric_type] = {
                "unit": row.unit,
                "values": [],
            }

        grouped[row.metric_type]["values"].append(row.value)

    metrics = {}

    for metric_type, data in grouped.items():
        values = data["values"]

        metrics[metric_type] = MetricStats(
            unit=data["unit"],
            count=len(values),
            average=sum(values) / len(values),
            minimum=min(values),
            maximum=max(values),
        )

    summary = SensorSummary(
        sensor_id=sensor_id,
        latest=latest,
        window_hours=1,
        metrics=metrics,
    )

    await redis_client.set(
        cache_key,
        summary.model_dump_json(),
        ex=30,
    )

    return summary