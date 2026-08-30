"""G_light via bedrock-tenants Function URL alias minilm-l12-h384.

Not a Bedrock Converse / GPU FM. The Lambda runs MiniLM-L12-H384 in-process
and returns JSON {"label","score","probs","tokens"} (unharmful / harmful).
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

MINILM_ALIAS = "minilm-l12-h384"
LAMBDA_NAME = "bedrock-inference-mvp"


def function_url(*, region: str = "us-east-1") -> str:
    raw = (os.environ.get("FUNCTION_URL") or os.environ.get("GASC_FUNCTION_URL") or "").strip()
    if raw:
        return raw.rstrip("/") + "/"
    import boto3

    url = boto3.client("lambda", region_name=region).get_function_url_config(FunctionName=LAMBDA_NAME)[
        "FunctionUrl"
    ]
    return str(url).rstrip("/") + "/"


def chat_completions(
    *,
    model: str,
    text: str,
    region: str = "us-east-1",
    max_tokens: int = 64,
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    url = function_url(region=region)
    key = os.environ.get("INFERENCE_API_KEY") or os.environ.get("API_KEY") or "1234"
    resp = httpx.post(
        f"{url}v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": text}],
            "max_tokens": max_tokens,
            "temperature": 0,
            "stream": False,
        },
        timeout=timeout_s,
    )
    resp.raise_for_status()
    return resp.json()


def score_minilm_remote(
    text: str,
    *,
    region: str = "us-east-1",
    tau: float = 0.50,
) -> tuple[float, str]:
    from gasc.risk import parse_minilm

    payload = chat_completions(model=MINILM_ALIAS, text=text, region=region)
    content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
    if isinstance(content, dict):
        content = json.dumps(content)
    return parse_minilm(str(content), tau=tau)
