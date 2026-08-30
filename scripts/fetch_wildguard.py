#!/usr/bin/env python3
"""Cache WildGuardTest native labels to data/external/wildguardtest.jsonl.

Requires Hugging Face access to allenai/wildguardmix after accepting the
gated-dataset form. Prefer `hf auth login` over a stale HF_TOKEN env var.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _hf_token() -> str | None:
    """Prefer the saved `hf auth login` token when HF_TOKEN disagrees with it."""
    env = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    stored_path = Path.home() / ".cache" / "huggingface" / "token"
    stored = stored_path.read_text().strip() if stored_path.is_file() else None
    if env and stored and env != stored:
        print(
            "warning: HF_TOKEN env is set and differs from `hf auth login`; "
            "using the saved login token. unset HF_TOKEN to silence this.",
            file=sys.stderr,
        )
        return stored
    return stored or env


def main() -> int:
    try:
        from huggingface_hub import hf_hub_download
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("pip install huggingface_hub pyarrow") from exc
    root = Path(__file__).resolve().parents[1]
    dest = root / "data" / "external"
    dest.mkdir(parents=True, exist_ok=True)
    parquet = hf_hub_download(
        repo_id="allenai/wildguardmix",
        filename="test/wildguard_test.parquet",
        repo_type="dataset",
        token=_hf_token(),
        local_dir=str(dest),
    )
    out = dest / "wildguardtest.jsonl"
    n = 0
    with out.open("w") as f:
        for rec in pq.read_table(parquet).to_pylist():
            label = rec.get("prompt_harm_label")
            if label not in {"harmful", "unharmful"}:
                continue
            f.write(
                json.dumps(
                    {
                        "prompt": rec.get("prompt"),
                        "prompt_harm_label": label,
                        "adversarial": rec.get("adversarial"),
                        "subcategory": rec.get("subcategory"),
                        "gt": "unsafe" if label == "harmful" else "safe",
                        "source": "wildguardtest",
                    }
                )
                + "\n"
            )
            n += 1
    print(f"wrote {n} rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
