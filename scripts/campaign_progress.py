#!/usr/bin/env python3
"""Progress + ETA for the E1–E6 rerun, parsed from the campaign log.

    python3 scripts/campaign_progress.py [results/rerun_provenance/campaign.log]

Planned seconds per cell come from each runner's DURATION_S; ETA scales the
remaining planned time by the observed wall/planned ratio so far.
"""

from __future__ import annotations

import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results/rerun_provenance/campaign.log"

# experiment: (cells, seconds per cell)  — reps × policies/variants × sweep points
PLAN = {
    "E1": (5 * 4 * 3, 40),
    "E2": (5 * 4 * 4, 120),
    "E3": (5 * 4, 480),
    "E4": (5 * 4, 420),
    "E5": (5 * 2 * 2, 60),
    "E6": (5 * 4, 120),
}
CELL = re.compile(r"^(E[1-6]) r\d+ ")


def main() -> int:
    if not LOG.exists():
        print(f"no log at {LOG}")
        return 1
    lines = LOG.read_text(errors="replace").splitlines()
    started = {e: sum(1 for l in lines if CELL.match(l) and l.startswith(e + " ")) for e in PLAN}
    finished = "exit" in (lines[-1] if lines else "")
    # the last started cell is still running unless the run has exited
    done = dict(started)
    if not finished:
        for e in reversed(list(PLAN)):
            if done[e]:
                done[e] -= 1
                break

    total_s = sum(n * s for n, s in PLAN.values())
    done_s = sum(done[e] * PLAN[e][1] for e in PLAN)
    t0 = LOG.stat().st_birthtime if hasattr(LOG.stat(), "st_birthtime") else LOG.stat().st_ctime
    wall = time.time() - t0

    print(f"{'exp':4} {'cells':>9} {'planned':>8}")
    for e, (n, s) in PLAN.items():
        mark = "✓" if done[e] == n else ("▶" if started[e] else " ")
        print(f"{e:4} {done[e]:>3}/{n:<5} {n * s / 60:>6.0f}m {mark}")
    pct = 100 * done_s / total_s
    print(f"\n{pct:5.1f}% of planned time  |  elapsed {timedelta(seconds=int(wall))}")
    if finished:
        print("run exited:", lines[-1])
    else:
        # E0b runs ~90 s before E1; trust the observed overhead ratio only after 10 min of cells
        ratio = max((wall - 90) / done_s, 1.0) if done_s >= 600 else 1.0
        left = (total_s - done_s) * ratio
        eta = datetime.now() + timedelta(seconds=left)
        basis = "observed pace" if done_s >= 600 else "planned durations"
        print(f"remaining ~{timedelta(seconds=int(left))}  →  ETA {eta:%a %H:%M}  ({basis})")
    errs = [l for l in lines if "Error" in l or "Traceback" in l]
    if errs:
        print("\n!! errors in log:", errs[-1][:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
