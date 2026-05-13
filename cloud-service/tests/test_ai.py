from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


def test_analyze_event_requires_credentials():
    client = TestClient(app)
    client.post(
        "/api/v1/edge/events",
        json={
            "event_id": "evt-ai-001",
            "room_id": "A101",
            "event_type": "HIGH_CO2",
            "level": "warning",
            "message": "A101 教室 CO2 浓度偏高",
            "metrics": {"avg_co2": 1260, "avg_temperature": 29.1, "max_people_count": 42},
            "timestamp": datetime(2026, 5, 13, 20, 0, 0).isoformat(),
        },
    )

    response = client.post("/api/v1/events/evt-ai-001/analyze", json={})

    assert response.status_code == 400
    assert "API key" in response.json()["detail"]
