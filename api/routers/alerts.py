import json
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from db.redis import get_client

router = APIRouter(prefix="/alerts", tags=["Alerts"])

ACTIVE_ALERTS_KEY = "alerts:active"
ALERT_CHANNEL = "alerts"
ALERT_SEQUENCE_KEY = "alerts:sequence"

class AlertCreate(BaseModel):
    node_id: str
    tag: str
    alarm_type: Literal["HH", "H", "L", "LL"]
    limit: float
    value: float
    priority: int
    message: str


@router.post("/publish", status_code=status.HTTP_201_CREATED)
async def publish_alert(alert: AlertCreate):
    redis = get_client()

    sequence = await redis.incr(ALERT_SEQUENCE_KEY)
    alert_id = f"ALR-{sequence:06d}"

    payload = {
        "alert_id": alert_id,
        "node_id": alert.node_id,
        "tag": alert.tag,
        "alarm_type": alert.alarm_type,
        "limit": alert.limit,
        "value": alert.value,
        "priority": alert.priority,
        "message": alert.message,
        "state": "ACTIVE",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    data = json.dumps(payload)

    await redis.hset(ACTIVE_ALERTS_KEY, alert_id, data)
    await redis.publish(ALERT_CHANNEL, data)

    return payload


@router.get("/active")
async def get_active_alerts():
    redis = get_client()
    values = await redis.hvals(ACTIVE_ALERTS_KEY)
    alerts = [json.loads(value) for value in values]

    return {
        "active": alerts,
        "count": len(alerts)
    }


@router.post("/{alert_id}/clear")
async def clear_alert(alert_id: str):
    redis = get_client()
    data = await redis.hget(ACTIVE_ALERTS_KEY, alert_id)
    if data is None: raise HTTPException(status_code=404, detail="Active alert not found")
    alert = json.loads(data)

    cleared_event = {
        **alert,
        "state": "CLEARED",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    await redis.hdel(ACTIVE_ALERTS_KEY, alert_id)
    await redis.publish(ALERT_CHANNEL, json.dumps(cleared_event))

    return cleared_event