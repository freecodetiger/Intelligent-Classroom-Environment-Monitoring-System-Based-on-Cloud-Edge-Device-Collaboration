from datetime import datetime
from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_ingest_aggregate_and_read_latest():
    client = TestClient(app)
    payload = {
        "device_id": "sensor-A101-001",
        "room_id": "A101",
        "window_size": 5,
        "avg_temperature": 29.1,
        "avg_humidity": 66.5,
        "avg_co2": 1230,
        "avg_light": 180,
        "max_people_count": 42,
        "timestamp": datetime(2026, 5, 13, 20, 0, 0).isoformat(),
    }

    assert client.post("/api/v1/edge/aggregate", json=payload).status_code == 200
    latest = client.get("/api/v1/rooms/A101/latest")

    assert latest.status_code == 200
    assert latest.json()["room_id"] == "A101"
    assert latest.json()["temperature"] == 29.1


def test_ingest_event_and_list_events():
    client = TestClient(app)
    payload = {
        "event_id": "evt-test-001",
        "room_id": "A101",
        "event_type": "HIGH_CO2",
        "level": "warning",
        "message": "A101 教室 CO2 浓度偏高",
        "metrics": {"avg_co2": 1230},
        "timestamp": datetime(2026, 5, 13, 20, 0, 0).isoformat(),
    }

    assert client.post("/api/v1/edge/events", json=payload).status_code == 200
    events = client.get("/api/v1/events")

    assert events.status_code == 200
    assert any(event["event_id"] == "evt-test-001" for event in events.json())


def test_room_history_returns_latest_hundred_points_in_chronological_order():
    client = TestClient(app)
    room_id = f"A199-HISTORY-{uuid4().hex[:8]}"
    base = datetime(2026, 5, 13, 20, 0, 0)

    for idx in range(105):
        payload = {
            "device_id": f"sensor-{room_id}",
            "room_id": room_id,
            "window_size": 5,
            "avg_temperature": 26.0 + idx * 0.01,
            "avg_humidity": 60.0,
            "avg_co2": 900 + idx,
            "avg_light": 180,
            "max_people_count": 30,
            "timestamp": (base + timedelta(seconds=idx)).isoformat(),
        }
        assert client.post("/api/v1/edge/aggregate", json=payload).status_code == 200

    history = client.get(f"/api/v1/rooms/{room_id}/history")

    assert history.status_code == 200
    rows = history.json()
    assert len(rows) == 100
    assert rows[0]["timestamp"] == (base + timedelta(seconds=5)).isoformat()
    assert rows[-1]["timestamp"] == (base + timedelta(seconds=104)).isoformat()
