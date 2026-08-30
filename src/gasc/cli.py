from __future__ import annotations

import argparse
from pathlib import Path

from gasc.config import load_config
from gasc.pipeline import run_pipeline
from gasc.report import write_metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gasc")
    parser.add_argument("-c", "--config", type=Path, default=Path("configs/smoke.yaml"))
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run")
    run_p.add_argument("--skip-llm", action="store_true")

    sub.add_parser("report")

    args = parser.parse_args(argv)
    cfg = load_config(args.config, skip_llm=bool(getattr(args, "skip_llm", False)))
    if args.cmd == "run":
        frozen = run_pipeline(cfg)
        write_metrics(cfg, n_frozen=len(frozen))
        print(f"froze {len(frozen)} prompts under {cfg.out}")
        return 0
    write_metrics(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
