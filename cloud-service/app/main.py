from __future__ import annotations

import json

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import AIAnalysis, Device, EdgeEvent, Room, SensorData
from app.schemas import AggregateIn, AnalyzeRequest, EventIn

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Classroom Cloud Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_room_and_device(db: Session, room_id: str, device_id: str | None = None) -> None:
    room = db.scalar(select(Room).where(Room.room_id == room_id))
    if room is None:
        db.add(Room(room_id=room_id, room_name=f"{room_id} 教室", building="教学楼", capacity=60))
    if device_id:
        device = db.scalar(select(Device).where(Device.device_id == device_id))
        if device is None:
            db.add(Device(device_id=device_id, room_id=room_id, device_type="sensor", status="online"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/edge/aggregate")
def receive_aggregate(payload: AggregateIn, db: Session = Depends(get_db)) -> dict[str, str]:
    ensure_room_and_device(db, payload.room_id, payload.device_id)
    db.add(
        SensorData(
            device_id=payload.device_id,
            room_id=payload.room_id,
            temperature=payload.avg_temperature,
            humidity=payload.avg_humidity,
            co2=payload.avg_co2,
            light=payload.avg_light,
            people_count=payload.max_people_count,
            source="edge",
            timestamp=payload.timestamp,
        )
    )
    db.commit()
    return {"message": "received"}


@app.post("/api/v1/edge/events")
def receive_event(payload: EventIn, db: Session = Depends(get_db)) -> dict[str, str]:
    ensure_room_and_device(db, payload.room_id)
    existing = db.scalar(select(EdgeEvent).where(EdgeEvent.event_id == payload.event_id))
    if existing is None:
        db.add(
            EdgeEvent(
                event_id=payload.event_id,
                room_id=payload.room_id,
                event_type=payload.event_type,
                level=payload.level,
                message=payload.message,
                metrics=json.dumps(payload.metrics, ensure_ascii=False),
                timestamp=payload.timestamp,
            )
        )
        db.commit()
    return {"message": "received"}


@app.get("/api/v1/rooms")
def list_rooms(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rooms = db.scalars(select(Room).order_by(Room.room_id)).all()
    return [
        {
            "room_id": room.room_id,
            "room_name": room.room_name,
            "building": room.building,
            "capacity": room.capacity,
        }
        for room in rooms
    ]


@app.get("/api/v1/rooms/{room_id}/latest")
def latest_room_data(room_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.scalar(
        select(SensorData)
        .where(SensorData.room_id == room_id)
        .order_by(desc(SensorData.timestamp), desc(SensorData.id))
    )
    if row is None:
        raise HTTPException(status_code=404, detail="room data not found")
    return {
        "room_id": row.room_id,
        "temperature": row.temperature,
        "humidity": row.humidity,
        "co2": row.co2,
        "light": row.light,
        "people_count": row.people_count,
        "timestamp": row.timestamp.isoformat(),
    }


@app.get("/api/v1/rooms/{room_id}/history")
def room_history(room_id: str, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.scalars(
        select(SensorData)
        .where(SensorData.room_id == room_id)
        .order_by(SensorData.timestamp, SensorData.id)
        .limit(100)
    ).all()
    return [
        {
            "room_id": row.room_id,
            "temperature": row.temperature,
            "humidity": row.humidity,
            "co2": row.co2,
            "light": row.light,
            "people_count": row.people_count,
            "timestamp": row.timestamp.isoformat(),
        }
        for row in rows
    ]


@app.get("/api/v1/events")
def list_events(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.scalars(select(EdgeEvent).order_by(desc(EdgeEvent.timestamp), desc(EdgeEvent.id)).limit(100)).all()
    return [
        {
            "event_id": row.event_id,
            "room_id": row.room_id,
            "event_type": row.event_type,
            "level": row.level,
            "message": row.message,
            "metrics": json.loads(row.metrics),
            "timestamp": row.timestamp.isoformat(),
        }
        for row in rows
    ]


@app.post("/api/v1/events/{event_id}/analyze")
async def analyze_event(event_id: str, request: AnalyzeRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    from app.ai_service import analyze_environment

    event = db.scalar(select(EdgeEvent).where(EdgeEvent.event_id == event_id))
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")

    event_payload = {
        "event_id": event.event_id,
        "room_id": event.room_id,
        "event_type": event.event_type,
        "level": event.level,
        "message": event.message,
        "metrics": json.loads(event.metrics),
        "timestamp": event.timestamp.isoformat(),
    }
    try:
        result = await analyze_environment(
            event_payload,
            request.api_key,
            request.base_url,
            request.model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI provider request failed: {exc}") from exc

    db.add(
        AIAnalysis(
            event_id=event.event_id,
            room_id=event.room_id,
            summary=str(result.get("summary", "")),
            impact=str(result.get("impact", "")),
            suggestions=json.dumps(result.get("suggestions", []), ensure_ascii=False),
            energy_saving=str(result.get("energy_saving", "")),
        )
    )
    db.commit()
    return result
