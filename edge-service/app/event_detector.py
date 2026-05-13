from __future__ import annotations

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
        events.append(
            EdgeEvent(
                room_id=room_id,
                event_type="HIGH_TEMPERATURE",
                level=level,
                message=f"{room_id} 教室温度偏高",
                metrics=metrics,
                timestamp=aggregate.timestamp,
            )
        )

    if aggregate.avg_co2 > 1000:
        level = "critical" if aggregate.avg_co2 > 1500 else "warning"
        events.append(
            EdgeEvent(
                room_id=room_id,
                event_type="HIGH_CO2",
                level=level,
                message=f"{room_id} 教室 CO2 浓度偏高，建议通风",
                metrics=metrics,
                timestamp=aggregate.timestamp,
            )
        )

    if aggregate.avg_light < 200 and aggregate.max_people_count > 0:
        events.append(
            EdgeEvent(
                room_id=room_id,
                event_type="LOW_LIGHT",
                level="info",
                message=f"{room_id} 教室光照不足",
                metrics=metrics,
                timestamp=aggregate.timestamp,
            )
        )

    if aggregate.max_people_count > 50:
        events.append(
            EdgeEvent(
                room_id=room_id,
                event_type="CROWD",
                level="critical",
                message=f"{room_id} 教室人数过多",
                metrics=metrics,
                timestamp=aggregate.timestamp,
            )
        )

    return events
