from __future__ import annotations

from collections import defaultdict
from time import monotonic

from fastapi import FastAPI

from app.cloud_client import CloudClient
from app.event_detector import detect_events
from app.schemas import SensorReading
from app.window import RoomWindow

app = FastAPI(title="Smart Classroom Edge Service")
cloud_client = CloudClient()
windows: dict[str, RoomWindow] = defaultdict(lambda: RoomWindow(size=5))
last_event_sent: dict[tuple[str, str], float] = {}
EVENT_COOLDOWN_SECONDS = 10


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/sensor/data")
async def receive_sensor_data(reading: SensorReading) -> dict[str, object]:
    window = windows[reading.room_id]
    window.add(reading)
    aggregate = window.aggregate()

    upload_errors: list[str] = []
    try:
        await cloud_client.send_aggregate(aggregate)
    except Exception as exc:
        upload_errors.append(f"aggregate upload failed: {exc}")

    sent_events = 0
    now = monotonic()
    for event in detect_events(reading.room_id, aggregate):
        key = (event.room_id, event.event_type)
        if now - last_event_sent.get(key, 0) < EVENT_COOLDOWN_SECONDS:
            continue

        last_event_sent[key] = now
        try:
            await cloud_client.send_event(event)
            sent_events += 1
        except Exception as exc:
            upload_errors.append(f"event upload failed: {exc}")

    return {
        "code": 0,
        "message": "received",
        "events_sent": sent_events,
        "upload_errors": upload_errors,
    }
