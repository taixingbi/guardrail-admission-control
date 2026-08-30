from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import ClientError

THROTTLE = {"ThrottlingException", "TooManyRequestsException", "ServiceQuotaExceededException"}


def bedrock_runtime(region: str = "us-east-1"):
    return boto3.client("bedrock-runtime", region_name=region)


def converse_text(client, *, model_id: str, user: str, max_tokens: int = 64, temperature: float = 0.0) -> str:
    resp = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": user}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    blocks = resp.get("output", {}).get("message", {}).get("content") or []
    return "".join(b.get("text", "") for b in blocks if "text" in b)


@dataclass
class StreamResult:
    text: str = ""
    ttft_ms: float | None = None
    e2e_ms: float = 0.0
    throttled: bool = False
    error: str | None = None


def converse_stream(
    client,
    *,
    model_id: str,
    user: str,
    max_tokens: int = 64,
    temperature: float = 0.0,
) -> StreamResult:
    t0 = time.time()
    first_ts: float | None = None
    parts: list[str] = []
    try:
        resp = client.converse_stream(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        for event in resp.get("stream") or []:
            if "contentBlockDelta" in event:
                if first_ts is None:
                    first_ts = time.time()
                piece = (event["contentBlockDelta"].get("delta") or {}).get("text") or ""
                if piece:
                    parts.append(piece)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        return StreamResult(
            e2e_ms=(time.time() - t0) * 1000,
            throttled=code in THROTTLE,
            error=str(exc),
        )
    finish = time.time()
    ttft_ms = None if first_ts is None else (first_ts - t0) * 1000
    return StreamResult(
        text="".join(parts),
        ttft_ms=ttft_ms,
        e2e_ms=(finish - t0) * 1000,
    )


def apply_guardrail(
    client,
    *,
    guardrail_id: str,
    guardrail_version: str,
    text: str,
) -> dict[str, Any]:
    try:
        resp = client.apply_guardrail(
            guardrailIdentifier=guardrail_id,
            guardrailVersion=guardrail_version,
            source="INPUT",
            content=[{"text": {"text": text}}],
        )
        return {
            "action": resp.get("action"),
            "outputs": resp.get("outputs") or [],
            "assessments": resp.get("assessments") or [],
            "throttled": False,
        }
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        return {"action": "ERROR", "error": str(exc), "throttled": code in THROTTLE}
