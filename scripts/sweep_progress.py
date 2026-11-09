#!/usr/bin/env python3
"""Progress + ETA for scripts/run_sweeps.py, parsed from results/rerun_provenance/sweeps.log."""

from __future__ import annotations

import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results/rerun_provenance/sweeps.log"
PLAN = {"rho": (5 * 3 * 2, 120), "deadline": (5 * 3 * 2, 120)}  # cells, planned s/cell
CELL = re.compile(r"^SWEEP (\w+) (\d+)/(\d+) ")


def main() -> int:
    lines = LOG.read_text(errors="replace").splitlines()
    started = {k: 0 for k in PLAN}
    for line in lines:
        m = CELL.match(line)
        if m:
            started[m.group(1)] = int(m.group(2))
    finished = bool(lines) and lines[-1].startswith("exit")
    done = dict(started)
    if not finished:
        for k in reversed(list(PLAN)):
            if done[k]:
                done[k] -= 1
                break
    total_s = sum(n * s for n, s in PLAN.values())
    done_s = sum(done[k] * PLAN[k][1] for k in PLAN)
    st = LOG.stat()
    wall = time.time() - getattr(st, "st_birthtime", st.st_ctime)
    for k, (n, s) in PLAN.items():
        mark = "✓" if done[k] == n else ("▶" if started[k] else " ")
        print(f"{k:9} {done[k]:>3}/{n:<4} {n * s / 60:>4.0f}m {mark}")
    print(f"\n{100 * done_s / total_s:5.1f}% of planned time  |  elapsed {timedelta(seconds=int(wall))}")
    if finished:
        print("run exited:", lines[-1])
    else:
        ratio = max(wall / done_s, 1.0) if done_s >= 600 else 1.0
        left = (total_s - done_s) * ratio
        print(f"remaining ~{timedelta(seconds=int(left))}  →  ETA {datetime.now() + timedelta(seconds=left):%a %H:%M}")
    errs = [l for l in lines if "Error" in l or "Traceback" in l]
    if errs:
        print("\n!! errors in log:", errs[-1][:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
