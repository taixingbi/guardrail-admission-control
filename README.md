# GASC

**GASC** — Guardrail Admission for Safety Capacity.

Multi-tenant gateway that treats **ApplyGuardrail as a finite shared safety resource** under a gateway-controlled budget \(B_g\) (not raw Bedrock capacity). Lightweight risk scores come from a **local MiniLM classifier**. Answers come from **Llama 4 Maverick 17B**. The scheduler chooses `direct` / `strong` / `reject` and never bypasses a required strong check (fail-closed).

Locked design: [docs/experiment-design.md](docs/experiment-design.md). Knobs: [FREEZE.md](FREEZE.md).

## Roles

| Role | Where | Purpose |
| --- | --- | --- |
| G_light | Local MiniLM | cheap risk estimation \(q(x)\) |
| G_strong | ApplyGuardrail | authoritative safety |
| LLM | Llama 4 Maverick 17B Instruct | user response |

Paper Tenant A/B are gateway policies, not AWS accounts. v1 runs in management `646821141010`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,g_light]"
cp .env.example .env
python scripts/fetch_wildguard_train.py
python scripts/train_g_light.py
python scripts/score_g_light.py
```

The paper needs:

1. AWS creds that can call Bedrock (same pattern as Paper 9: local gateway → Converse / ApplyGuardrail). v1 uses management `646821141010`.
2. Llama 4 Maverick enabled. G_light is a local MiniLM classifier (not Nova Micro).
3. A Guardrail ID in `.env` as `GASC_GUARDRAIL_ID`.

```bash
./scripts/create-guardrail.sh   # once; writes GASC_GUARDRAIL_ID
./scripts/smoke-bedrock.sh      # apply-guardrail + llama4-maverick (Nova Micro is appendix-only)
```

## Run

Offline smoke (fixtures, no Bedrock):

```bash
gasc -c configs/smoke.yaml run --skip-llm
pytest
```

Gateway:

```bash
uvicorn gateway.app.main:app --port 8080
```

## Pipeline

| Stage | Output |
| --- | --- |
| P1 | `data/runs/<id>/1_seeds/seeds.jsonl` |
| P2 | `2_validated_seeds/validated_seeds.jsonl` |
| P3 | `3_variants/variants.jsonl` |
| P4 | `4_validated_prompts/prompts.jsonl` (frozen) |
| P5 | `5_runs/run_records.jsonl` |
| P6 | `6_metrics/metrics.json` |

Ground truth must not use Nova Micro, ApplyGuardrail, or Maverick.
