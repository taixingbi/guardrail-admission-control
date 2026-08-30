# GASC

**GASC** — Guardrail Admission for Safety Capacity.

Multi-tenant gateway that treats Amazon Bedrock **ApplyGuardrail** as a finite shared safety resource. Lightweight risk scores come from **Nova Micro**. Answers come from **Llama 4 Maverick 17B**. The scheduler chooses `direct` / `strong` / `reject` and never bypasses a required strong check (fail-closed).

Locked design: [docs/experiment-design.md](docs/experiment-design.md). Knobs: [FREEZE.md](FREEZE.md).

## Roles

| Role | Bedrock | Purpose |
| --- | --- | --- |
| G_light | Nova Micro | cheap risk estimation |
| G_strong | ApplyGuardrail | authoritative safety |
| LLM | Llama 4 Maverick 17B Instruct | user response |

Paper Tenant A/B are gateway policies, not AWS accounts. v1 runs in management `646821141010`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

The paper needs:

1. AWS creds that can call Bedrock (same pattern as Paper 9: local gateway → Converse / ApplyGuardrail). v1 uses management `646821141010`.
2. Nova Micro and Llama 4 Maverick enabled in that account.
3. A Guardrail ID in `.env` as `GASC_GUARDRAIL_ID`.

```bash
./scripts/create-guardrail.sh   # once; writes GASC_GUARDRAIL_ID
./scripts/smoke-bedrock.sh      # nova-micro, apply-guardrail, llama4-maverick
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
