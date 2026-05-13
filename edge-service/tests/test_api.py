from datetime import datetime

from fastapi.testclient import TestClient

from app import main


def test_sensor_data_endpoint_accepts_valid_payload(monkeypatch):
    async def fake_send_aggregate(payload):
        return None

    async def fake_send_event(payload):
        return None

    monkeypatch.setattr(main.cloud_client, "send_aggregate", fake_send_aggregate)
    monkeypatch.setattr(main.cloud_client, "send_event", fake_send_event)
    client = TestClient(main.app)
    response = client.post(
        "/api/v1/sensor/data",
        json={
            "device_id": "sensor-A101-001",
            "room_id": "A101",
            "temperature": 29.1,
            "humidity": 66.5,
            "co2": 1230,
            "light": 180,
            "people_count": 42,
            "timestamp": datetime(2026, 5, 13, 20, 0, 0).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "received"


def test_sensor_data_endpoint_rejects_invalid_payload():
    client = TestClient(main.app)
    response = client.post(
        "/api/v1/sensor/data",
        json={
            "device_id": "sensor-A101-001",
            "room_id": "A101",
            "temperature": 999,
            "humidity": 66.5,
            "co2": 1230,
            "light": 180,
            "people_count": 42,
            "timestamp": datetime(2026, 5, 13, 20, 0, 0).isoformat(),
        },
    )

    assert response.status_code == 422
