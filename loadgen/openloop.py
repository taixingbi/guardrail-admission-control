from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx
import yaml

from gasc.io import load_jsonl
from gasc.schemas import FrozenPrompt


def main() -> int:
    parser = argparse.ArgumentParser(description="Open-loop replay of frozen prompts")
    parser.add_argument("-c", "--config", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--prompts", type=Path, default=Path("data/runs/smoke/4_validated_prompts/prompts.jsonl"))
    args = parser.parse_args()
    spec = yaml.safe_load(args.config.read_text()) or {}
    rps = float(spec.get("rps", 1.0))
    prompts = load_jsonl(args.prompts, FrozenPrompt)
    if not prompts:
        raise SystemExit("no frozen prompts")
    delay = 1.0 / max(rps, 0.01)
    tenants = spec.get("tenants") or ["A", "B"]
    with httpx.Client(timeout=30.0) as client:
        for i, prompt in enumerate(prompts):
            tenant = tenants[i % len(tenants)]
            q = {"S0": 0.05, "S1": 0.45, "S2": 0.9, "S3": 0.95}[prompt.variant]
            client.post(
                f"{args.base_url.rstrip('/')}/v1/infer",
                json={
                    "tenant_id": tenant,
                    "text": prompt.text,
                    "q": q,
                    "variant": prompt.variant,
                    "gt_label": prompt.target_label,
                },
            )
            time.sleep(delay)
    print(json.dumps({"sent": len(prompts), "rps": rps}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
