# Smart Classroom P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable local P0 cloud-edge-device smart classroom monitoring system with sensor simulation, edge processing, cloud storage, AI analysis, and a React dashboard.

**Architecture:** The project is split into four local processes: `sensor-simulator` posts raw data to `edge-service`; `edge-service` validates, aggregates, detects events, and posts processed data to `cloud-service`; `cloud-service` stores data in SQLite and calls an OpenAI-compatible model API; `frontend` reads cloud APIs and displays the dashboard.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy, SQLite, httpx, pytest, React, Vite, TypeScript, ECharts, lucide-react.

---

## File Structure

- Create `README.md`: local run instructions and architecture summary.
- Create `.gitignore`: ignore virtualenvs, SQLite files, generated browser mockups, and frontend build output.
- Create `sensor-simulator/`: Python simulator CLI.
- Create `edge-service/app/`: FastAPI edge service, windowing, detection, cloud client.
- Create `cloud-service/app/`: FastAPI cloud service, SQLite models, routers, AI service.
- Create `frontend/`: React + Vite dashboard.
- Create `tests/`: Python tests for edge logic and cloud API behavior.

## Task 1: Repository Baseline

**Files:**
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
.DS_Store
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
*.db
*.sqlite
.env
node_modules/
dist/
.superpowers/
```

- [ ] **Step 2: Create root `README.md`**

```markdown
# 智慧教室环境监测系统 P0

本项目实现一个本地可运行的云边端协同智慧教室检测系统：

```text
sensor-simulator -> edge-service -> cloud-service + SQLite -> frontend
```

## 本地端口

- cloud-service: http://localhost:8000
- edge-service: http://localhost:8001
- frontend: http://localhost:5173

## 快速启动

分别打开四个终端：

```bash
cd cloud-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
cd edge-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

```bash
cd sensor-simulator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --mode mixed --interval 1
```

```bash
cd frontend
npm install
npm run dev
```

## AI 配置

前端设置页可以填写 OpenAI-compatible API Key、Base URL 和模型名。云端也支持 `.env`：

```env
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```
```

- [ ] **Step 3: Verify baseline files**

Run: `ls -la && test -f README.md && test -f .gitignore`

Expected: command exits with code `0`.

## Task 2: Edge Domain Logic

**Files:**
- Create: `edge-service/requirements.txt`
- Create: `edge-service/app/__init__.py`
- Create: `edge-service/app/schemas.py`
- Create: `edge-service/app/window.py`
- Create: `edge-service/app/event_detector.py`
- Test: `edge-service/tests/test_processing.py`

- [ ] **Step 1: Create `edge-service/requirements.txt`**

```text
fastapi==0.115.12
uvicorn[standard]==0.34.2
pydantic==2.11.4
httpx==0.28.1
pytest==8.3.5
```

- [ ] **Step 2: Write failing edge processing tests**

```python
# edge-service/tests/test_processing.py
from datetime import datetime

from app.event_detector import detect_events
from app.schemas import SensorReading
from app.window import RoomWindow


def reading(temp=29.0, co2=1200.0, light=180.0, people=42):
    return SensorReading(
        device_id="sensor-A101-001",
        room_id="A101",
        temperature=temp,
        humidity=66.0,
        co2=co2,
        light=light,
        people_count=people,
        timestamp=datetime(2026, 5, 13, 20, 0, 0),
    )


def test_window_aggregates_recent_readings():
    window = RoomWindow(size=3)
    window.add(reading(temp=26, co2=800, light=300, people=20))
    window.add(reading(temp=28, co2=1000, light=260, people=35))
    window.add(reading(temp=30, co2=1200, light=220, people=40))

    aggregate = window.aggregate()

    assert aggregate.avg_temperature == 28
    assert aggregate.avg_co2 == 1000
    assert aggregate.max_people_count == 40


def test_detector_generates_expected_events():
    window = RoomWindow(size=5)
    for _ in range(5):
        window.add(reading(temp=30, co2=1300, light=150, people=55))

    events = detect_events("A101", window.aggregate())
    event_types = {event.event_type for event in events}

    assert {"HIGH_TEMPERATURE", "HIGH_CO2", "LOW_LIGHT", "CROWD"} <= event_types
    assert any(event.level == "critical" for event in events)
```

- [ ] **Step 3: Run tests and verify they fail**

Run: `cd edge-service && pytest -q`

Expected: fails with import errors because `app.event_detector`, `app.schemas`, and `app.window` do not exist yet.

- [ ] **Step 4: Implement edge schemas**

```python
# edge-service/app/schemas.py
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
```

- [ ] **Step 5: Implement sliding window**

```python
# edge-service/app/window.py
from collections import deque
from dataclasses import dataclass

from app.schemas import AggregatePayload, SensorReading


@dataclass(frozen=True)
class WindowAggregate:
    device_id: str
    room_id: str
    window_size: int
    avg_temperature: float
    avg_humidity: float
    avg_co2: float
    avg_light: float
    max_people_count: int
    timestamp: object


class RoomWindow:
    def __init__(self, size: int = 5) -> None:
        self.size = size
        self._items: deque[SensorReading] = deque(maxlen=size)

    def add(self, reading: SensorReading) -> None:
        self._items.append(reading)

    def is_ready(self) -> bool:
        return len(self._items) > 0

    def aggregate(self) -> AggregatePayload:
        if not self._items:
            raise ValueError("cannot aggregate an empty window")
        items = list(self._items)
        count = len(items)
        latest = items[-1]
        return AggregatePayload(
            device_id=latest.device_id,
            room_id=latest.room_id,
            window_size=count,
            avg_temperature=round(sum(x.temperature for x in items) / count, 2),
            avg_humidity=round(sum(x.humidity for x in items) / count, 2),
            avg_co2=round(sum(x.co2 for x in items) / count, 2),
            avg_light=round(sum(x.light for x in items) / count, 2),
            max_people_count=max(x.people_count for x in items),
            timestamp=latest.timestamp,
        )
```

- [ ] **Step 6: Implement event detector**

```python
# edge-service/app/event_detector.py
from app.schemas import AggregatePayload, EdgeEvent


def detect_events(room_id: str, aggregate: AggregatePayload) -> list[EdgeEvent]:
    metrics = {
        "avg_temperature": aggregate.avg_temperature,
        "avg_humidity": aggregate.avg_humidity,
        "avg_co2": aggregate.avg_co2,
        "avg_light": aggregate.avg_light,
        "max_people_count": aggregate.max_people_count,
    }
    events: list[EdgeEvent] = []

    if aggregate.avg_temperature > 28:
        level = "critical" if aggregate.avg_temperature > 32 else "warning"
        events.append(EdgeEvent(room_id=room_id, event_type="HIGH_TEMPERATURE", level=level, message=f"{room_id} 教室温度偏高", metrics=metrics, timestamp=aggregate.timestamp))

    if aggregate.avg_co2 > 1000:
        level = "critical" if aggregate.avg_co2 > 1500 else "warning"
        events.append(EdgeEvent(room_id=room_id, event_type="HIGH_CO2", level=level, message=f"{room_id} 教室 CO2 浓度偏高，建议通风", metrics=metrics, timestamp=aggregate.timestamp))

    if aggregate.avg_light < 200 and aggregate.max_people_count > 0:
        events.append(EdgeEvent(room_id=room_id, event_type="LOW_LIGHT", level="info", message=f"{room_id} 教室光照不足", metrics=metrics, timestamp=aggregate.timestamp))

    if aggregate.max_people_count > 50:
        events.append(EdgeEvent(room_id=room_id, event_type="CROWD", level="critical", message=f"{room_id} 教室人数过多", metrics=metrics, timestamp=aggregate.timestamp))

    return events
```

- [ ] **Step 7: Run edge tests**

Run: `cd edge-service && pytest -q`

Expected: `2 passed`.

## Task 3: Edge FastAPI Service

**Files:**
- Create: `edge-service/app/cloud_client.py`
- Create: `edge-service/app/main.py`
- Test: `edge-service/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

```python
# edge-service/tests/test_api.py
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


def test_sensor_data_endpoint_accepts_valid_payload():
    client = TestClient(app)
    response = client.post("/api/v1/sensor/data", json={
        "device_id": "sensor-A101-001",
        "room_id": "A101",
        "temperature": 29.1,
        "humidity": 66.5,
        "co2": 1230,
        "light": 180,
        "people_count": 42,
        "timestamp": datetime(2026, 5, 13, 20, 0, 0).isoformat(),
    })

    assert response.status_code == 200
    assert response.json()["message"] == "received"


def test_sensor_data_endpoint_rejects_invalid_payload():
    client = TestClient(app)
    response = client.post("/api/v1/sensor/data", json={
        "device_id": "sensor-A101-001",
        "room_id": "A101",
        "temperature": 999,
        "humidity": 66.5,
        "co2": 1230,
        "light": 180,
        "people_count": 42,
        "timestamp": datetime(2026, 5, 13, 20, 0, 0).isoformat(),
    })

    assert response.status_code == 422
```

- [ ] **Step 2: Implement cloud client**

```python
# edge-service/app/cloud_client.py
import os

import httpx

from app.schemas import AggregatePayload, EdgeEvent


class CloudClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("CLOUD_BASE_URL") or "http://localhost:8000").rstrip("/")

    async def send_aggregate(self, payload: AggregatePayload) -> None:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{self.base_url}/api/v1/edge/aggregate", json=payload.model_dump(mode="json"))

    async def send_event(self, event: EdgeEvent) -> None:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{self.base_url}/api/v1/edge/events", json=event.model_dump(mode="json"))
```

- [ ] **Step 3: Implement edge app**

```python
# edge-service/app/main.py
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

    return {"code": 0, "message": "received", "events_sent": sent_events, "upload_errors": upload_errors}
```

- [ ] **Step 4: Run edge tests**

Run: `cd edge-service && pytest -q`

Expected: all edge tests pass.

## Task 4: Cloud Persistence And APIs

**Files:**
- Create: `cloud-service/requirements.txt`
- Create: `cloud-service/app/__init__.py`
- Create: `cloud-service/app/database.py`
- Create: `cloud-service/app/models.py`
- Create: `cloud-service/app/schemas.py`
- Create: `cloud-service/app/main.py`
- Test: `cloud-service/tests/test_api.py`

- [ ] **Step 1: Create `cloud-service/requirements.txt`**

```text
fastapi==0.115.12
uvicorn[standard]==0.34.2
pydantic==2.11.4
sqlalchemy==2.0.40
httpx==0.28.1
pytest==8.3.5
```

- [ ] **Step 2: Write failing cloud API tests**

```python
# cloud-service/tests/test_api.py
from datetime import datetime

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
```

- [ ] **Step 3: Implement database setup**

```python
# cloud-service/app/database.py
import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smart_classroom.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Implement models**

```python
# cloud-service/app/models.py
from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    room_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    building: Mapped[str | None] = mapped_column(String(128), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
```

- [ ] **Step 5: Implement schemas**

```python
# cloud-service/app/schemas.py
from datetime import datetime
from typing import Any

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
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
```

- [ ] **Step 6: Implement cloud app APIs**

```python
# cloud-service/app/main.py
import json

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import EdgeEvent, Room, SensorData
from app.schemas import AggregateIn, AnalyzeRequest, EventIn

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Smart Classroom Cloud Service")


def ensure_room(db: Session, room_id: str) -> None:
    room = db.scalar(select(Room).where(Room.room_id == room_id))
    if room is None:
        db.add(Room(room_id=room_id, room_name=f"{room_id} 教室", building="教学楼", capacity=60))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/edge/aggregate")
def receive_aggregate(payload: AggregateIn, db: Session = Depends(get_db)) -> dict[str, str]:
    ensure_room(db, payload.room_id)
    db.add(SensorData(
        device_id=payload.device_id,
        room_id=payload.room_id,
        temperature=payload.avg_temperature,
        humidity=payload.avg_humidity,
        co2=payload.avg_co2,
        light=payload.avg_light,
        people_count=payload.max_people_count,
        source="edge",
        timestamp=payload.timestamp,
    ))
    db.commit()
    return {"message": "received"}


@app.post("/api/v1/edge/events")
def receive_event(payload: EventIn, db: Session = Depends(get_db)) -> dict[str, str]:
    ensure_room(db, payload.room_id)
    existing = db.scalar(select(EdgeEvent).where(EdgeEvent.event_id == payload.event_id))
    if existing is None:
        db.add(EdgeEvent(
            event_id=payload.event_id,
            room_id=payload.room_id,
            event_type=payload.event_type,
            level=payload.level,
            message=payload.message,
            metrics=json.dumps(payload.metrics, ensure_ascii=False),
            timestamp=payload.timestamp,
        ))
        db.commit()
    return {"message": "received"}


@app.get("/api/v1/rooms")
def list_rooms(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rooms = db.scalars(select(Room).order_by(Room.room_id)).all()
    return [{"room_id": room.room_id, "room_name": room.room_name, "building": room.building, "capacity": room.capacity} for room in rooms]


@app.get("/api/v1/rooms/{room_id}/latest")
def latest_room_data(room_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.scalar(select(SensorData).where(SensorData.room_id == room_id).order_by(desc(SensorData.timestamp)))
    if row is None:
        raise HTTPException(status_code=404, detail="room data not found")
    return {"room_id": row.room_id, "temperature": row.temperature, "humidity": row.humidity, "co2": row.co2, "light": row.light, "people_count": row.people_count, "timestamp": row.timestamp.isoformat()}


@app.get("/api/v1/rooms/{room_id}/history")
def room_history(room_id: str, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.scalars(select(SensorData).where(SensorData.room_id == room_id).order_by(SensorData.timestamp).limit(100)).all()
    return [{"room_id": row.room_id, "temperature": row.temperature, "humidity": row.humidity, "co2": row.co2, "light": row.light, "people_count": row.people_count, "timestamp": row.timestamp.isoformat()} for row in rows]


@app.get("/api/v1/events")
def list_events(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.scalars(select(EdgeEvent).order_by(desc(EdgeEvent.timestamp)).limit(100)).all()
    return [{"event_id": row.event_id, "room_id": row.room_id, "event_type": row.event_type, "level": row.level, "message": row.message, "metrics": json.loads(row.metrics), "timestamp": row.timestamp.isoformat()} for row in rows]


@app.post("/api/v1/events/{event_id}/analyze")
def analyze_event(event_id: str, request: AnalyzeRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    event = db.scalar(select(EdgeEvent).where(EdgeEvent.event_id == event_id))
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    raise HTTPException(status_code=501, detail="AI service will be implemented in Task 5")
```

- [ ] **Step 7: Run cloud tests**

Run: `cd cloud-service && pytest -q`

Expected: ingestion and query tests pass; no AI test exists yet.

## Task 5: Cloud AI Service

**Files:**
- Create: `cloud-service/app/ai_service.py`
- Modify: `cloud-service/app/main.py`
- Test: `cloud-service/tests/test_ai.py`

- [ ] **Step 1: Write AI error-path test**

```python
# cloud-service/tests/test_ai.py
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


def test_analyze_event_requires_credentials():
    client = TestClient(app)
    client.post("/api/v1/edge/events", json={
        "event_id": "evt-ai-001",
        "room_id": "A101",
        "event_type": "HIGH_CO2",
        "level": "warning",
        "message": "A101 教室 CO2 浓度偏高",
        "metrics": {"avg_co2": 1260, "avg_temperature": 29.1, "max_people_count": 42},
        "timestamp": datetime(2026, 5, 13, 20, 0, 0).isoformat(),
    })

    response = client.post("/api/v1/events/evt-ai-001/analyze", json={})

    assert response.status_code == 400
    assert "API key" in response.json()["detail"]
```

- [ ] **Step 2: Implement AI service**

```python
# cloud-service/app/ai_service.py
import json
import os
from typing import Any

import httpx


async def analyze_environment(event: dict[str, Any], api_key: str | None, base_url: str | None, model: str | None) -> dict[str, Any]:
    resolved_key = api_key or os.getenv("OPENAI_API_KEY")
    resolved_base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    resolved_model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    if not resolved_key:
        raise ValueError("API key is required")

    prompt = (
        "你是一个智慧教室环境管理助手。请根据事件数据输出 JSON，字段必须包含 "
        "summary, impact, suggestions, energy_saving。事件数据："
        + json.dumps(event, ensure_ascii=False)
    )
    payload = {
        "model": resolved_model,
        "messages": [
            {"role": "system", "content": "你只输出 JSON，不输出 Markdown。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {resolved_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{resolved_base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)
```

- [ ] **Step 3: Wire AI service into cloud app**

Replace the existing `analyze_event` function in `cloud-service/app/main.py` with:

```python
@app.post("/api/v1/events/{event_id}/analyze")
async def analyze_event(event_id: str, request: AnalyzeRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    from app.ai_service import analyze_environment
    from app.models import AIAnalysis

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
        result = await analyze_environment(event_payload, request.api_key, request.base_url, request.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI provider request failed: {exc}") from exc

    db.add(AIAnalysis(
        event_id=event.event_id,
        room_id=event.room_id,
        summary=str(result.get("summary", "")),
        impact=str(result.get("impact", "")),
        suggestions=json.dumps(result.get("suggestions", []), ensure_ascii=False),
        energy_saving=str(result.get("energy_saving", "")),
    ))
    db.commit()
    return result
```

- [ ] **Step 4: Run cloud tests**

Run: `cd cloud-service && pytest -q`

Expected: all cloud tests pass.

## Task 6: Sensor Simulator

**Files:**
- Create: `sensor-simulator/requirements.txt`
- Create: `sensor-simulator/main.py`

- [ ] **Step 1: Create requirements**

```text
httpx==0.28.1
```

- [ ] **Step 2: Implement simulator**

```python
# sensor-simulator/main.py
import argparse
import asyncio
import random
from datetime import datetime

import httpx


ROOMS = ["A101", "A102", "B201"]


def make_reading(room_id: str, mode: str) -> dict[str, object]:
    base = {
        "normal": (25, 55, 650, 360, 24),
        "hot": (31, 62, 850, 320, 35),
        "co2": (28, 66, 1350, 260, 44),
        "low_light": (26, 58, 760, 150, 30),
        "crowd": (29, 64, 1250, 230, 56),
        "mixed": (30, 66, 1300, 170, 52),
    }[mode]
    temperature, humidity, co2, light, people = base
    return {
        "device_id": f"sensor-{room_id}-001",
        "room_id": room_id,
        "temperature": round(temperature + random.uniform(-1.2, 1.2), 1),
        "humidity": round(humidity + random.uniform(-4, 4), 1),
        "co2": round(co2 + random.uniform(-120, 120), 1),
        "light": round(light + random.uniform(-40, 40), 1),
        "people_count": max(0, int(people + random.randint(-4, 4))),
        "timestamp": datetime.now().isoformat(),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edge-url", default="http://localhost:8001")
    parser.add_argument("--mode", choices=["normal", "hot", "co2", "low_light", "crowd", "mixed"], default="normal")
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    async with httpx.AsyncClient(timeout=5) as client:
        while True:
            for room_id in ROOMS:
                payload = make_reading(room_id, args.mode)
                response = await client.post(f"{args.edge_url}/api/v1/sensor/data", json=payload)
                print(response.status_code, payload)
            await asyncio.sleep(args.interval)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Verify CLI help**

Run: `cd sensor-simulator && python main.py --help`

Expected: help text lists `--edge-url`, `--mode`, and `--interval`.

## Task 7: Frontend Dashboard

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`

- [ ] **Step 1: Create package metadata**

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.4.1",
    "echarts": "^5.6.0",
    "lucide-react": "^0.511.0",
    "vite": "^6.3.5",
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@types/react": "^19.1.3",
    "@types/react-dom": "^19.1.3",
    "typescript": "^5.8.3"
  }
}
```

- [ ] **Step 2: Create Vite shell**

```html
<!-- frontend/index.html -->
<div id="root"></div>
<script type="module" src="/src/main.tsx"></script>
```

```json
// frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
```

```ts
// frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
```

```tsx
// frontend/src/main.tsx
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(<App />);
```

- [ ] **Step 3: Implement dashboard**

```tsx
// frontend/src/App.tsx
import { Activity, Bot, Building2, RefreshCw, Settings } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

type Room = { room_id: string; room_name?: string };
type Metric = { room_id: string; temperature: number; humidity: number; co2: number; light: number; people_count: number; timestamp: string };
type EventItem = { event_id: string; room_id: string; event_type: string; level: string; message: string; timestamp: string; metrics: Record<string, unknown> };

export default function App() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selectedRoom, setSelectedRoom] = useState("A101");
  const [latest, setLatest] = useState<Metric | null>(null);
  const [history, setHistory] = useState<Metric[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [apiKey, setApiKey] = useState(localStorage.getItem("llm_api_key") ?? "");
  const [baseUrl, setBaseUrl] = useState(localStorage.getItem("llm_base_url") ?? "https://api.openai.com/v1");
  const [model, setModel] = useState(localStorage.getItem("llm_model") ?? "gpt-4o-mini");
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  async function refresh() {
    setError("");
    const [roomRes, eventRes] = await Promise.all([fetch(`${API_BASE}/api/v1/rooms`), fetch(`${API_BASE}/api/v1/events`)]);
    if (roomRes.ok) setRooms(await roomRes.json());
    if (eventRes.ok) setEvents(await eventRes.json());
    const latestRes = await fetch(`${API_BASE}/api/v1/rooms/${selectedRoom}/latest`);
    if (latestRes.ok) setLatest(await latestRes.json());
    const historyRes = await fetch(`${API_BASE}/api/v1/rooms/${selectedRoom}/history`);
    if (historyRes.ok) setHistory(await historyRes.json());
  }

  useEffect(() => {
    refresh().catch((exc) => setError(String(exc)));
    const id = window.setInterval(() => refresh().catch(() => undefined), 5000);
    return () => window.clearInterval(id);
  }, [selectedRoom]);

  const selectedEvents = useMemo(() => events.filter((event) => event.room_id === selectedRoom), [events, selectedRoom]);

  async function analyze(eventId: string) {
    localStorage.setItem("llm_api_key", apiKey);
    localStorage.setItem("llm_base_url", baseUrl);
    localStorage.setItem("llm_model", model);
    setError("");
    setAnalysis(null);
    const response = await fetch(`${API_BASE}/api/v1/events/${eventId}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey, base_url: baseUrl, model }),
    });
    if (!response.ok) {
      const body = await response.json();
      setError(body.detail ?? "AI analysis failed");
      return;
    }
    setAnalysis(await response.json());
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><Building2 size={20} />智慧教室监测</div>
        <button className="nav active"><Activity size={16} />总览</button>
        <button className="nav"><Bot size={16} />AI 建议</button>
        <button className="nav"><Settings size={16} />设置</button>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            <h1>{selectedRoom} 实时状态</h1>
            <p>本地 P0 云边端协同检测系统</p>
          </div>
          <button className="iconButton" onClick={refresh}><RefreshCw size={18} />刷新</button>
        </header>

        {error && <div className="error">{error}</div>}

        <section className="roomTabs">
          {["A101", "A102", "B201", ...rooms.map((room) => room.room_id)].filter((value, index, arr) => arr.indexOf(value) === index).map((roomId) => (
            <button key={roomId} className={selectedRoom === roomId ? "selected" : ""} onClick={() => setSelectedRoom(roomId)}>{roomId}</button>
          ))}
        </section>

        <section className="metrics">
          <MetricCard label="温度" value={latest ? `${latest.temperature.toFixed(1)} C` : "--"} />
          <MetricCard label="湿度" value={latest ? `${latest.humidity.toFixed(1)}%` : "--"} />
          <MetricCard label="CO2" value={latest ? `${latest.co2.toFixed(0)} ppm` : "--"} />
          <MetricCard label="光照" value={latest ? `${latest.light.toFixed(0)} lux` : "--"} />
          <MetricCard label="人数" value={latest ? String(latest.people_count) : "--"} />
        </section>

        <section className="grid">
          <div className="panel">
            <h2>历史数据</h2>
            <div className="chartRows">
              {history.slice(-20).map((item) => <div key={item.timestamp} className="bar" style={{ width: `${Math.min(100, item.co2 / 18)}%` }}>{Math.round(item.co2)} ppm</div>)}
            </div>
          </div>
          <div className="panel">
            <h2>模型设置</h2>
            <input type="password" placeholder="API Key" value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
            <input placeholder="Base URL" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
            <input placeholder="Model" value={model} onChange={(event) => setModel(event.target.value)} />
          </div>
        </section>

        <section className="panel">
          <h2>异常事件</h2>
          <div className="events">
            {selectedEvents.map((event) => (
              <div className="event" key={event.event_id}>
                <div><b>{event.event_type}</b><span>{event.level}</span><p>{event.message}</p></div>
                <button onClick={() => analyze(event.event_id)}>生成 AI 建议</button>
              </div>
            ))}
            {selectedEvents.length === 0 && <p className="empty">暂无异常事件，启动 mixed 模式模拟器后会出现数据。</p>}
          </div>
        </section>

        {analysis && <section className="panel"><h2>AI 建议</h2><pre>{JSON.stringify(analysis, null, 2)}</pre></section>}
      </main>
    </div>
  );
}

function MetricCard(props: { label: string; value: string }) {
  return <div className="metric"><span>{props.label}</span><strong>{props.value}</strong></div>;
}
```

- [ ] **Step 4: Implement styles**

```css
/* frontend/src/styles.css */
* { box-sizing: border-box; }
body { margin: 0; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #eef2f6; color: #172033; }
button, input { font: inherit; }
.shell { min-height: 100vh; display: grid; grid-template-columns: 232px 1fr; }
.sidebar { background: #141922; color: #f8fafc; padding: 20px 14px; }
.brand { display: flex; gap: 10px; align-items: center; font-weight: 700; margin-bottom: 24px; }
.nav { width: 100%; border: 0; background: transparent; color: #cbd5e1; display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px; cursor: pointer; }
.nav.active, .nav:hover { background: #263142; color: white; }
.main { padding: 24px; }
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
h1 { margin: 0; font-size: 26px; }
p { margin: 0; color: #667085; }
.iconButton, .event button { display: inline-flex; align-items: center; gap: 8px; border: 1px solid #cbd5e1; background: white; border-radius: 8px; padding: 9px 12px; cursor: pointer; }
.roomTabs { display: flex; gap: 8px; margin-bottom: 16px; }
.roomTabs button { border: 1px solid #cbd5e1; background: white; border-radius: 8px; padding: 8px 14px; cursor: pointer; }
.roomTabs .selected { background: #1f6feb; border-color: #1f6feb; color: white; }
.metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.metric, .panel { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 16px; }
.metric span { color: #667085; display: block; margin-bottom: 8px; }
.metric strong { font-size: 24px; }
.grid { display: grid; grid-template-columns: 1.4fr .8fr; gap: 16px; margin-bottom: 16px; }
h2 { font-size: 18px; margin: 0 0 12px; }
.chartRows { display: flex; flex-direction: column; gap: 6px; min-height: 210px; }
.bar { min-width: 56px; background: #dbeafe; color: #1d4ed8; border-radius: 6px; padding: 5px 8px; font-size: 12px; white-space: nowrap; }
input { width: 100%; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }
.events { display: grid; gap: 10px; }
.event { display: flex; justify-content: space-between; gap: 16px; align-items: center; border-top: 1px solid #edf2f7; padding-top: 10px; }
.event span { margin-left: 8px; color: #b45309; font-size: 12px; }
.empty { padding: 16px 0; }
.error { background: #fee2e2; color: #991b1b; padding: 10px 12px; border-radius: 8px; margin-bottom: 12px; }
pre { white-space: pre-wrap; background: #f8fafc; border-radius: 8px; padding: 12px; }
@media (max-width: 900px) { .shell { grid-template-columns: 1fr; } .sidebar { display: none; } .metrics, .grid { grid-template-columns: 1fr; } }
```

- [ ] **Step 5: Build frontend**

Run: `cd frontend && npm install && npm run build`

Expected: TypeScript and Vite build complete successfully.

## Task 8: End-To-End Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run backend tests**

Run:

```bash
cd edge-service && pytest -q
cd ../cloud-service && pytest -q
```

Expected: all Python tests pass.

- [ ] **Step 2: Start cloud service**

Run: `cd cloud-service && uvicorn app.main:app --reload --port 8000`

Expected: `Uvicorn running on http://127.0.0.1:8000`.

- [ ] **Step 3: Start edge service**

Run: `cd edge-service && uvicorn app.main:app --reload --port 8001`

Expected: `Uvicorn running on http://127.0.0.1:8001`.

- [ ] **Step 4: Start simulator**

Run: `cd sensor-simulator && python main.py --mode mixed --interval 1`

Expected: console prints `200` responses for classroom payloads.

- [ ] **Step 5: Confirm cloud has data**

Run:

```bash
curl http://localhost:8000/api/v1/rooms/A101/latest
curl http://localhost:8000/api/v1/events
```

Expected: latest data returns `room_id: A101`; events include `HIGH_CO2`, `HIGH_TEMPERATURE`, `LOW_LIGHT`, or `CROWD`.

- [ ] **Step 6: Start frontend**

Run: `cd frontend && npm run dev -- --host 127.0.0.1`

Expected: Vite prints `http://127.0.0.1:5173`.

- [ ] **Step 7: Update README with final verification notes**

Append:

```markdown
## 验证结果

- Edge tests: pass
- Cloud tests: pass
- Frontend build: pass
- End-to-end data flow: sensor simulator can create A101 data and cloud APIs return latest metrics and abnormal events.
```

- [ ] **Step 8: Final verification**

Run:

```bash
cd edge-service && pytest -q
cd ../cloud-service && pytest -q
cd ../frontend && npm run build
```

Expected: all commands pass.

## Self-Review

Spec coverage:

- Sensor simulator is covered by Task 6.
- Edge validation, sliding window, aggregation, and event detection are covered by Tasks 2 and 3.
- Cloud SQLite persistence and query APIs are covered by Task 4.
- Real model API integration with user-supplied credentials is covered by Task 5.
- React dashboard and settings page are covered by Task 7.
- End-to-end verification is covered by Task 8.

Scope check:

- Redis Stream, WebSocket, Docker, MySQL, and login are intentionally absent from implementation tasks, matching the P0 spec.

Placeholder scan:

- The plan contains no `TBD`, unresolved optional tasks, or undefined follow-up sections.
