from __future__ import annotations

import json
import os
from typing import Any

import httpx

DEFAULT_GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_GLM_MODEL = "glm-4-flash"


def _extract_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


async def analyze_environment(
    event: dict[str, Any],
) -> dict[str, Any]:
    resolved_key = (os.getenv("GLM_API_KEY") or "").strip()
    resolved_base_url = (os.getenv("GLM_BASE_URL") or DEFAULT_GLM_BASE_URL).rstrip("/")
    resolved_model = (os.getenv("GLM_MODEL") or DEFAULT_GLM_MODEL).strip()
    if not resolved_key:
        raise ValueError("GLM API key is required")

    prompt = (
        "你是一个智慧教室环境管理助手。请根据以下异常事件数据生成简洁、可执行的管理建议。"
        "必须输出 JSON，不要输出 Markdown。JSON 字段必须包含 summary, impact, suggestions, energy_saving。"
        f"异常事件数据：{json.dumps(event, ensure_ascii=False)}"
    )
    payload = {
        "model": resolved_model,
        "messages": [
            {"role": "system", "content": "你只输出 JSON，不输出 Markdown。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {resolved_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{resolved_base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    result = _extract_json(content)
    return {
        "summary": str(result.get("summary", "")),
        "impact": str(result.get("impact", "")),
        "suggestions": result.get("suggestions", []),
        "energy_saving": str(result.get("energy_saving", "")),
    }
