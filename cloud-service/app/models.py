from __future__ import annotations

from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    room_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    building: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    room_id: Mapped[str] = mapped_column(String(64), index=True)
    device_type: Mapped[str] = mapped_column(String(64), default="sensor")
    status: Mapped[str] = mapped_column(String(32), default="online")
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())


class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    room_id: Mapped[str] = mapped_column(String(64), index=True)
    temperature: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)
    co2: Mapped[float] = mapped_column(Float)
    light: Mapped[float] = mapped_column(Float)
    people_count: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32), default="edge")
    timestamp: Mapped[object] = mapped_column(DateTime, index=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())


class EdgeEvent(Base):
    __tablename__ = "edge_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    room_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    level: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    metrics: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[object] = mapped_column(DateTime, index=True)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), index=True)
    room_id: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(Text)
    suggestions: Mapped[str] = mapped_column(Text)
    energy_saving: Mapped[str] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())
