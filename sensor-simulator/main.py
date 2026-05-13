from __future__ import annotations

import argparse
import asyncio
import random
from datetime import datetime

import httpx

ROOMS = ["A101", "A102", "B201"]
MODE_BASELINES = {
    "normal": (25, 55, 650, 360, 24),
    "hot": (31, 62, 850, 320, 35),
    "co2": (28, 66, 1350, 260, 44),
    "low_light": (26, 58, 760, 150, 30),
    "crowd": (29, 64, 1250, 230, 56),
    "mixed": (30, 66, 1300, 170, 52),
}


def make_reading(room_id: str, mode: str) -> dict[str, object]:
    temperature, humidity, co2, light, people = MODE_BASELINES[mode]
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


async def run(edge_url: str, mode: str, interval: float) -> None:
    async with httpx.AsyncClient(timeout=5) as client:
        while True:
            for room_id in ROOMS:
                payload = make_reading(room_id, mode)
                response = await client.post(f"{edge_url.rstrip('/')}/api/v1/sensor/data", json=payload)
                print(response.status_code, payload)
            await asyncio.sleep(interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smart classroom sensor simulator")
    parser.add_argument("--edge-url", default="http://localhost:8001")
    parser.add_argument("--mode", choices=list(MODE_BASELINES), default="normal")
    parser.add_argument("--interval", type=float, default=1.0)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.edge_url, args.mode, args.interval))
