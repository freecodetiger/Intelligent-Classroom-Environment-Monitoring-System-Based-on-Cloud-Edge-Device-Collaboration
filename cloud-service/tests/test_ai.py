from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app
from app.models import AIAnalysis


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


def test_list_ai_analysis_records():
    db: Session = SessionLocal()
    db.add(
        AIAnalysis(
            event_id="evt-analysis-list-001",
            room_id="A101",
            summary="A101 教室 CO2 偏高",
            impact="可能影响注意力",
            suggestions='["开启通风设备"]',
            energy_saving="无人后关闭新风",
        )
    )
    db.commit()
    db.close()

    client = TestClient(app)
    response = client.get("/api/v1/analysis")

    assert response.status_code == 200
    assert any(item["event_id"] == "evt-analysis-list-001" for item in response.json())
