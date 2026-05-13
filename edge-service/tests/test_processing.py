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
