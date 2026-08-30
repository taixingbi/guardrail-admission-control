from __future__ import annotations

import json
import re
from typing import Literal

_JSON = re.compile(r"\{.*\}", re.DOTALL)


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
    try:
        q = float(data.get("q", 1.0))
    except (TypeError, ValueError):
        return 1.0, "REVIEW"
    q = min(1.0, max(0.0, q))
    label = str(data.get("label", "REVIEW")).upper()
    if label not in {"SAFE", "REVIEW"}:
        label = "REVIEW" if q >= 0.5 else "SAFE"
    if label == "SAFE" and q >= 0.5:
        label = "REVIEW"
    return q, label  # type: ignore[return-value]
