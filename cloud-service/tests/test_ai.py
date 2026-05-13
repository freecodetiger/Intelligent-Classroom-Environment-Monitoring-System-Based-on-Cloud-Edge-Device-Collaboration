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
    assert "GLM API key" in response.json()["detail"]


def test_analyze_event_ignores_request_credentials(monkeypatch):
    captured = {}

    async def fake_post(self, url, headers=None, json=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": '{"summary":"ok","impact":"low","suggestions":["open window"],"energy_saving":"save"}'
                            }
                        }
                    ]
                }

        return Response()

    monkeypatch.setenv("GLM_API_KEY", "server-key")
    monkeypatch.setenv("GLM_BASE_URL", "https://server.example/v1")
    monkeypatch.setenv("GLM_MODEL", "server-model")
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    client = TestClient(app)
    client.post(
        "/api/v1/edge/events",
        json={
            "event_id": "evt-ai-fixed-provider-001",
            "room_id": "A101",
            "event_type": "HIGH_CO2",
            "level": "warning",
            "message": "A101 教室 CO2 浓度偏高",
            "metrics": {"avg_co2": 1260, "avg_temperature": 29.1, "max_people_count": 42},
            "timestamp": datetime(2026, 5, 13, 20, 0, 0).isoformat(),
        },
    )

    response = client.post(
        "/api/v1/events/evt-ai-fixed-provider-001/analyze",
        json={"api_key": "user-key", "base_url": "https://user.example/v1", "model": "user-model"},
    )

    assert response.status_code == 200
    assert captured["url"] == "https://server.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer server-key"
    assert captured["json"]["model"] == "server-model"


def test_analyze_event_uses_full_glm_api_url(monkeypatch):
    captured = {}

    async def fake_post(self, url, headers=None, json=None):
        captured["url"] = url
        captured["json"] = json

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": '{"summary":"ok","impact":"low","suggestions":["open window"],"energy_saving":"save"}'
                            }
                        }
                    ]
                }

        return Response()

    monkeypatch.setenv("GLM_API_KEY", "server-key")
    monkeypatch.delenv("GLM_BASE_URL", raising=False)
    monkeypatch.setenv("GLM_API_URL", "https://glm.example/v4/chat/completions")
    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)

    client = TestClient(app)
    client.post(
        "/api/v1/edge/events",
        json={
            "event_id": "evt-ai-full-url-001",
            "room_id": "A101",
            "event_type": "HIGH_CO2",
            "level": "warning",
            "message": "A101 教室 CO2 浓度偏高",
            "metrics": {"avg_co2": 1260, "avg_temperature": 29.1, "max_people_count": 42},
            "timestamp": datetime(2026, 5, 13, 20, 0, 0).isoformat(),
        },
    )

    response = client.post("/api/v1/events/evt-ai-full-url-001/analyze", json={})

    assert response.status_code == 200
    assert captured["url"] == "https://glm.example/v4/chat/completions"
    assert captured["json"]["model"] == "GLM-4.7-Flash"


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
