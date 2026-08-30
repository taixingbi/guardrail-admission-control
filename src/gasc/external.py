"""External sets use native labels. Do not retune tau."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from gasc.paths import repo_root
from gasc.schemas import FrozenPrompt

EXTERNAL_DIR = repo_root() / "data" / "external"
TAU_FROZEN = 0.50


def native_gt(source: str, raw_label: str | None) -> str | None:
    label = (raw_label or "").strip().lower()
    if source == "xstest":
        if label in {"safe", "unsafe"}:
            return label
        return None
    if source == "wildguardtest":
        if label in {"harmful", "unsafe"}:
            return "unsafe"
        if label in {"unharmful", "safe"}:
            return "safe"
        return None
    return None


def load_xstest(path: Path | None = None) -> list[FrozenPrompt]:
    csv_path = path or EXTERNAL_DIR / "xstest_prompts.csv"
    jsonl_path = EXTERNAL_DIR / "xstest.jsonl"
    rows: list[FrozenPrompt] = []
    if jsonl_path.exists() and path is None:
        for line in jsonl_path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            gt = native_gt("xstest", rec.get("gt") or rec.get("label"))
            if gt is None or not rec.get("prompt"):
                continue
            rows.append(
                FrozenPrompt(
                    variant_id=f"xs_{rec.get('id', len(rows)+1)}",
                    seed_id=str(rec.get("id") or rec.get("type") or "xs"),
                    variant="S2" if gt == "unsafe" else "S0",
                    text=rec["prompt"],
                    target_label=gt,  # type: ignore[arg-type]
                    metadata={"source": "xstest", "type": rec.get("type")},
                )
            )
        return rows
    with csv_path.open() as f:
        for rec in csv.DictReader(f):
            gt = native_gt("xstest", rec.get("label"))
            if gt is None or not rec.get("prompt"):
                continue
            rows.append(
                FrozenPrompt(
                    variant_id=f"xs_{rec.get('id', len(rows)+1)}",
                    seed_id=str(rec.get("id") or "xs"),
                    variant="S2" if gt == "unsafe" else "S0",
                    text=rec["prompt"],
                    target_label=gt,  # type: ignore[arg-type]
                    metadata={"source": "xstest", "type": rec.get("type")},
                )
            )
    return rows


def load_wildguardtest(path: Path | None = None) -> list[FrozenPrompt]:
    jsonl_path = path or EXTERNAL_DIR / "wildguardtest.jsonl"
    if not jsonl_path.exists():
        raise FileNotFoundError(
            f"{jsonl_path} missing. Download WildGuardTest (allenai/wildguardmix, "
            "wildguardtest split) and write native-labeled jsonl."
        )
    rows: list[FrozenPrompt] = []
    for i, line in enumerate(jsonl_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        rec = json.loads(line)
        gt = native_gt("wildguardtest", rec.get("gt") or rec.get("prompt_harm_label"))
        text = rec.get("prompt") or rec.get("text")
        if gt is None or not text:
            continue
        rows.append(
            FrozenPrompt(
                variant_id=f"wg_{i:04d}",
                seed_id=f"wg_{i:04d}",
                variant="S3" if rec.get("adversarial") else ("S2" if gt == "unsafe" else "S0"),
                text=text,
                target_label=gt,  # type: ignore[arg-type]
                metadata={
                    "source": "wildguardtest",
                    "adversarial": rec.get("adversarial"),
                    "subcategory": rec.get("subcategory"),
                },
            )
        )
    return rows
