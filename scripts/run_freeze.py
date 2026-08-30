#!/usr/bin/env python3
"""P1–P4 freeze: 500 seeds × S0–S3, independent Claude judge, complete families only."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from gasc.config import load_config
from gasc.io import load_jsonl
from gasc.pipeline import run_pipeline
from gasc.schemas import VariantValidation


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    cfg = load_config(root / "configs" / "main.yaml")
    frozen = run_pipeline(cfg)
    val_path = cfg.out / "4_validated_prompts" / "all_validations.jsonl"
    vals = load_jsonl(val_path, VariantValidation) if val_path.exists() else []
    by_var = Counter(v.variant for v in frozen)
    agree = sum(1 for v in vals if v.judge_agrees)
    summary = {
        "n_seeds_requested": cfg.seed_limit,
        "n_frozen_prompts": len(frozen),
        "n_complete_families": len(frozen) // 4,
        "by_variant": dict(by_var),
        "n_judged": len(vals),
        "judge_agree": agree,
        "judge_agree_rate": (agree / len(vals)) if vals else None,
        "judge_model": cfg.models.judge,
        "out": str(cfg.out),
    }
    out = root / "results" / "freeze"
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# Main freeze (P1–P4)",
        "",
        f"Seeds requested: {cfg.seed_limit}. Frozen prompts: {len(frozen)} "
        f"({len(frozen) // 4} complete S0–S3 families).",
        f"Judge: `{cfg.models.judge}` (not Nova Micro / ApplyGuardrail / Maverick).",
        f"Judge agree: {agree}/{len(vals)}.",
        "",
        "A family is kept only if all four variants pass structural checks and the judge.",
        f"Output: `{cfg.out}`",
    ]
    (out / "metrics.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
