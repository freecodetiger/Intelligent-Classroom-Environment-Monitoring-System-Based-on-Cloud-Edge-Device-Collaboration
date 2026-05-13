from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AggregateIn(BaseModel):
    device_id: str
    room_id: str
    window_size: int
    avg_temperature: float
    avg_humidity: float
    avg_co2: float
    avg_light: float
    max_people_count: int
    timestamp: datetime


class EventIn(BaseModel):
    event_id: str
    room_id: str
    event_type: str
    level: str
    message: str
    metrics: dict[str, Any]
    timestamp: datetime


class AnalyzeRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
