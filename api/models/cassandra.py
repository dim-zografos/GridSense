from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class SensorReading(BaseModel):
    sensor_id: str
    reading_time: datetime
    metric_type: str
    value: float
    unit: str
    quality_flag: int = Field(ge=0, le=2)

class SensorReadingResponse(BaseModel):
    message: str

class MetricStats(BaseModel):
    unit: str
    count: int
    average: float
    minimum: float
    maximum: float

class SensorSummary(BaseModel):
    sensor_id: str
    latest: Optional[SensorReading] = None
    window_hours: int
    metrics: dict[str, MetricStats]