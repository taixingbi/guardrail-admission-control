#!/usr/bin/env python3
"""Replay E1–E6 on the P4 freeze. Scout results in results/eN stay untouched."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    scripts = ["run_e1.py", "run_e2.py", "run_e5.py", "run_e6.py", "run_e3.py", "run_e4.py"]
    for name in scripts:
        print(f"=== replay {name} ===", flush=True)
        proc = subprocess.run([sys.executable, str(root / "scripts" / name)], cwd=root)
        if proc.returncode != 0:
            return proc.returncode
    print("replay done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
