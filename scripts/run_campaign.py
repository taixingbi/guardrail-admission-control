#!/usr/bin/env python3
"""Final clean campaign. Does not redesign experiments.

    python3 scripts/run_campaign.py          # e0a → e1–e6 → e2e
    python3 scripts/run_campaign.py e0a
    python3 scripts/run_campaign.py e1-e6
    python3 scripts/run_campaign.py e2e

E0a scores freeze + XSTest + WildGuardTest via minilm-l12-h384 Function URL
and freezes q(x). E1–E6 replay that q (5 reps). One live e2e sanity, then STOP.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = {
    "e0a": ["scripts/score_g_light.py"],
    "e1": ["scripts/run_e1.py"],
    "e2": ["scripts/run_e2.py"],
    "e3": ["scripts/run_e3.py"],
    "e4": ["scripts/run_e4.py"],
    "e5": ["scripts/run_e5.py"],
    "e6": ["scripts/run_e6.py"],
    "e2e": ["scripts/run_e2e.py"],
}
ORDER = ("e0a", "e1", "e2", "e3", "e4", "e5", "e6", "e2e")


def _run(script: str) -> None:
    cmd = [sys.executable, str(ROOT / script)]
    print(f"\n=== {script} ===\n", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    arg = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower()
    if arg in {"all", ""}:
        stages = list(ORDER)
    elif arg in {"e1-e6", "e1–e6"}:
        stages = ["e1", "e2", "e3", "e4", "e5", "e6"]
    elif arg in STAGES:
        stages = [arg]
    else:
        raise SystemExit(f"unknown stage {arg!r}; use all | e0a | e1-e6 | e2e | e1…e6")
    for name in stages:
        _run(STAGES[name][0])
    print("\nCampaign stage(s) done. Do not retune τ/Bg. No E7/E8.\n", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
