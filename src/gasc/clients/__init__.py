from __future__ import annotations

from gasc.clients.bedrock import bedrock_runtime, converse_text
from gasc.paths import repo_root
from gasc.risk import parse_risk


def g_light_user_prompt(text: str) -> str:
    template = (repo_root() / "prompts" / "g_light.txt").read_text(encoding="utf-8")
    return template.replace("{{text}}", text)


def score_risk(text: str, *, model_id: str, region: str = "us-east-1") -> tuple[float, str]:
    """Local MiniLM by default. Nova Micro only if GASC_GLIGHT_BACKEND=nova."""
    import os

    if os.environ.get("GASC_GLIGHT_BACKEND", "local").strip().lower() != "nova":
        from gasc.g_light import score_local

        q, label, _ms = score_local(text)
        return q, label
    raw = converse_text(
        bedrock_runtime(region),
        model_id=model_id,
        user=g_light_user_prompt(text),
        max_tokens=64,
        temperature=0.0,
    )
    return parse_risk(raw)
