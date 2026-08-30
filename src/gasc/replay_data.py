"""Load the P4 freeze for E1–E6 replay. Falls back to fixture smoke if missing."""

from __future__ import annotations

import json
from pathlib import Path

from gasc.config import load_config
from gasc.io import load_jsonl
from gasc.paths import repo_root
from gasc.pipeline import run_pipeline
from gasc.schemas import FrozenPrompt

FROZEN_PROMPTS = repo_root() / "data" / "runs" / "main" / "4_validated_prompts" / "prompts.jsonl"
E0A_SCORES = repo_root() / "results" / "replay" / "e0a" / "scores.jsonl"


def load_replay_prompts() -> list[FrozenPrompt]:
    if FROZEN_PROMPTS.exists():
        return load_jsonl(FROZEN_PROMPTS, FrozenPrompt)
    cfg = load_config(repo_root() / "configs" / "e0a.yaml", skip_llm=True)
    return run_pipeline(cfg)


def load_live_q(path: Path | None = None) -> dict[str, float]:
    """E0a Nova Micro q by variant_id. Empty if the E0a replay has not been run."""
    scores = path or E0A_SCORES
    if not scores.exists():
        return {}
    out: dict[str, float] = {}
    for line in scores.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        vid = rec.get("variant_id")
        if vid is None or rec.get("q") is None:
            continue
        out[str(vid)] = float(rec["q"])
    return out


def q_for(prompt: FrozenPrompt, live_q: dict[str, float] | None = None) -> float:
    if live_q and prompt.variant_id in live_q:
        return live_q[prompt.variant_id]
    return 1.0 if prompt.target_label == "unsafe" else 0.0


def split_safe_unsafe(prompts: list[FrozenPrompt]) -> tuple[list[FrozenPrompt], list[FrozenPrompt]]:
    safe = [p for p in prompts if p.target_label == "safe"]
    unsafe = [p for p in prompts if p.target_label == "unsafe"]
    if not safe or not unsafe:
        raise RuntimeError(f"replay set missing a class: safe={len(safe)} unsafe={len(unsafe)}")
    return safe, unsafe


def replay_dir(experiment: str) -> Path:
    out = repo_root() / "results" / "replay" / experiment
    out.mkdir(parents=True, exist_ok=True)
    return out
