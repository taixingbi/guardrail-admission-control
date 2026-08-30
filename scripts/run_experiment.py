#!/usr/bin/env python3
"""Thin experiment runner. Loadgen + optional local gateway."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    return subprocess.call(
        [
            sys.executable,
            str(root / "loadgen" / "openloop.py"),
            "-c",
            str(args.config),
            "--base-url",
            args.base_url,
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
