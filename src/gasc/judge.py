"""Independent freeze judge. Must not be Nova Micro, ApplyGuardrail, or Maverick."""

from __future__ import annotations

import json
import re
import time
from gasc.clients.bedrock import converse_text
from gasc.paths import repo_root
from gasc.schemas import GtLabel, PromptVariant

PROMPT_PATH = repo_root() / "prompts" / "judge.txt"
_FORBIDDEN_SUBSTR = ("nova-micro", "llama4-maverick", "applyguardrail")


def render_judge_prompt(variant: PromptVariant) -> str:
    template = PROMPT_PATH.read_text()
    return template.replace("{{variant}}", variant.variant).replace("{{text}}", variant.text)


def parse_judge_label(text: str) -> GtLabel | None:
    raw = (text or "").strip()
    if not raw:
        return None
    match = re.search(r"\{.*\}", raw, flags=re.S)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    label = str(payload.get("label") or "").strip().lower()
    if label in {"safe", "unsafe"}:
        return label  # type: ignore[return-value]
    return None


def assert_judge_model_allowed(model_id: str) -> None:
    lowered = model_id.lower()
    if any(token in lowered for token in _FORBIDDEN_SUBSTR):
        raise ValueError(f"judge must be independent of system models, got {model_id}")


def judge_label(client, *, model_id: str, variant: PromptVariant, retries: int = 4) -> GtLabel | None:
    assert_judge_model_allowed(model_id)
    prompt = render_judge_prompt(variant)
    delay = 1.0
    for attempt in range(retries):
        try:
            text = converse_text(client, model_id=model_id, user=prompt, max_tokens=128, temperature=0.0)
            return parse_judge_label(text)
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(delay)
            delay = min(delay * 2, 16.0)
    return None
