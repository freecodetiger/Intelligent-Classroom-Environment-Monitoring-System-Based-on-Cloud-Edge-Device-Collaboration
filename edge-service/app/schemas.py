from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    device_id: str
    room_id: str
    temperature: float = Field(ge=-20, le=60)
    humidity: float = Field(ge=0, le=100)
    co2: float = Field(ge=300, le=5000)
    light: float = Field(ge=0)
    people_count: int = Field(ge=0)
    timestamp: datetime


class AggregatePayload(BaseModel):
    device_id: str
    room_id: str
    window_size: int
    avg_temperature: float
    avg_humidity: float
    avg_co2: float
    avg_light: float
    max_people_count: int
    timestamp: datetime


class EdgeEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt-{uuid4().hex[:12]}")
    room_id: str
    event_type: str
    level: str
    message: str
    metrics: dict[str, Any]
    timestamp: datetime
