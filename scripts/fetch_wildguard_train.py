#!/usr/bin/env python3
"""Cache WildGuardMix *train* (not test) for local G_light. Freeze stays held-out."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _hf_token() -> str | None:
    env = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    stored_path = Path.home() / ".cache" / "huggingface" / "token"
    stored = stored_path.read_text().strip() if stored_path.is_file() else None
    if env and stored and env != stored:
        return stored
    return stored or env


def main() -> int:
    try:
        from huggingface_hub import hf_hub_download, list_repo_files
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit("pip install huggingface_hub pyarrow") from exc
    root = Path(__file__).resolve().parents[1]
    dest = root / "data" / "external"
    dest.mkdir(parents=True, exist_ok=True)
    token = _hf_token()
    files = list_repo_files("allenai/wildguardmix", repo_type="dataset", token=token)
    candidates = [f for f in files if "train" in f.lower() and f.endswith(".parquet")]
    if not candidates:
        raise SystemExit(f"no train parquet in allenai/wildguardmix: {files[:20]}")
    name = sorted(candidates, key=len)[0]
    print(f"downloading {name}", flush=True)
    parquet = hf_hub_download(
        repo_id="allenai/wildguardmix",
        filename=name,
        repo_type="dataset",
        token=token,
        local_dir=str(dest),
    )
    out = dest / "wildguardtrain.jsonl"
    n = 0
    with out.open("w") as f:
        for rec in pq.read_table(parquet).to_pylist():
            label = rec.get("prompt_harm_label")
            if label not in {"harmful", "unharmful"}:
                continue
            text = rec.get("prompt") or rec.get("text")
            if not text:
                continue
            f.write(
                json.dumps(
                    {
                        "prompt": text,
                        "prompt_harm_label": label,
                        "gt": "unsafe" if label == "harmful" else "safe",
                        "source": "wildguardtrain",
                    }
                )
                + "\n"
            )
            n += 1
    print(f"wrote {n} rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
