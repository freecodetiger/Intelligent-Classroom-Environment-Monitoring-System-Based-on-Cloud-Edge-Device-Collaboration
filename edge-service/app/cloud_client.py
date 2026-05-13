from __future__ import annotations

import os

import httpx

from app.schemas import AggregatePayload, EdgeEvent


class CloudClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("CLOUD_BASE_URL") or "http://localhost:8000").rstrip("/")

    async def send_aggregate(self, payload: AggregatePayload) -> None:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/edge/aggregate",
                json=payload.model_dump(mode="json"),
            )
            response.raise_for_status()

    async def send_event(self, event: EdgeEvent) -> None:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/edge/events",
                json=event.model_dump(mode="json"),
            )
            response.raise_for_status()
