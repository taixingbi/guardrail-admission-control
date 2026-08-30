from __future__ import annotations

import json
import re
from typing import Any, Literal

_JSON = re.compile(r"\{.*\}", re.DOTALL)


def _clip_q(value: Any, default: float = 1.0) -> float:
    try:
        q = float(value)
    except (TypeError, ValueError):
        return default
    return min(1.0, max(0.0, q))


def parse_risk(raw: str) -> tuple[float, Literal["SAFE", "REVIEW"]]:
    """Parse G_light JSON. Fail-closed: unparsable → REVIEW, q=1.0."""
    text = (raw or "").strip()
    match = _JSON.search(text)
    if not match:
        return 1.0, "REVIEW"
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return 1.0, "REVIEW"
    if "probs" in data or str(data.get("label", "")).lower() in {"harmful", "unharmful"}:
        return parse_minilm(match.group(0))
    q = _clip_q(data.get("q", 1.0))
    label = str(data.get("label", "REVIEW")).upper()
    if label not in {"SAFE", "REVIEW"}:
        label = "REVIEW" if q >= 0.5 else "SAFE"
    if label == "SAFE" and q >= 0.5:
        label = "REVIEW"
    return q, label  # type: ignore[return-value]


def parse_minilm(raw: str, *, tau: float = 0.50) -> tuple[float, Literal["SAFE", "REVIEW"]]:
    """Parse Lambda MiniLM JSON {"label","score","probs"} → (q, SAFE|REVIEW)."""
    text = (raw or "").strip()
    match = _JSON.search(text)
    if not match:
        return 1.0, "REVIEW"
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return 1.0, "REVIEW"
    probs = data.get("probs") if isinstance(data.get("probs"), dict) else {}
    if "harmful" in probs:
        q = _clip_q(probs["harmful"])
    else:
        lab = str(data.get("label", "")).lower()
        score = _clip_q(data.get("score", 1.0))
        q = score if lab in {"harmful", "unsafe", "review"} else (1.0 - score if lab in {"unharmful", "safe"} else 1.0)
    label: Literal["SAFE", "REVIEW"] = "REVIEW" if q >= tau else "SAFE"
    return q, label
