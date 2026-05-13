from __future__ import annotations

from collections import deque

from app.schemas import AggregatePayload, SensorReading


class RoomWindow:
    def __init__(self, size: int = 5) -> None:
        self.size = size
        self._items: deque[SensorReading] = deque(maxlen=size)

    def add(self, reading: SensorReading) -> None:
        self._items.append(reading)

    def is_ready(self) -> bool:
        return bool(self._items)

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
            avg_temperature=round(sum(item.temperature for item in items) / count, 2),
            avg_humidity=round(sum(item.humidity for item in items) / count, 2),
            avg_co2=round(sum(item.co2 for item in items) / count, 2),
            avg_light=round(sum(item.light for item in items) / count, 2),
            max_people_count=max(item.people_count for item in items),
            timestamp=latest.timestamp,
        )
