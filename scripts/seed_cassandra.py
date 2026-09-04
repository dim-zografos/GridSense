import os
import zlib
from datetime import datetime, timedelta, timezone

from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args


NUM_SENSORS = 30
READINGS_PER_SENSOR = 2000
NUM_SHARDS = 4

BASE_TIME = datetime(2026, 9, 1, tzinfo=timezone.utc)


def seed_cassandra():
    print("Seeding Cassandra...")

    cluster = Cluster(
        [os.getenv("CASSANDRA_HOST")],
        port=int(os.getenv("CASSANDRA_PORT"))
    )

    session = cluster.connect(os.getenv("CASSANDRA_KEYSPACE"))

    try:
        reading_query = session.prepare("""
            INSERT INTO sensor_readings (
                sensor_id,
                reading_time,
                metric_type,
                value,
                unit,
                quality_flag
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """)

        bucket_query = session.prepare("""
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
        """)

        readings = []
        bucket_readings = []

        metrics = [
            ("voltage", "V"),
            ("current", "A"),
            ("power_factor", "PF"),
        ]

        for sensor_number in range(1, NUM_SENSORS + 1):
            sensor_id = f"SM_{sensor_number:05d}"
            shard = zlib.crc32(sensor_id.encode()) % NUM_SHARDS

            for i in range(READINGS_PER_SENSOR):
                reading_time = BASE_TIME + timedelta(seconds=i * 5)

                metric_type, unit = metrics[i % len(metrics)]

                if metric_type == "voltage":
                    value = 225 + ((sensor_number + i) % 31) * 0.5

                elif metric_type == "current":
                    value = 10 + ((sensor_number + i) % 81) * 0.5

                else:
                    value = 0.90 + ((sensor_number + i) % 10) * 0.01

                quality_flag = (
                    2 if (i + 1) % 200 == 0
                    else 1 if (i + 1) % 50 == 0
                    else 0
                )

                readings.append((
                    sensor_id,
                    reading_time,
                    metric_type,
                    value,
                    unit,
                    quality_flag,
                ))

                bucket_readings.append((
                    reading_time.replace(second=0, microsecond=0),
                    shard,
                    reading_time,
                    sensor_id,
                    metric_type,
                    value,
                    unit,
                    quality_flag,
                ))

        execute_concurrent_with_args(
            session,
            reading_query,
            readings,
            concurrency=50,
            raise_on_first_error=True,
        )

        execute_concurrent_with_args(
            session,
            bucket_query,
            bucket_readings,
            concurrency=50,
            raise_on_first_error=True,
        )

        print(f"Cassandra seeded successfully: {NUM_SENSORS} sensors, {READINGS_PER_SENSOR} readings per sensor")

    finally:
        cluster.shutdown()