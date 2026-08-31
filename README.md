# GASC

**GASC** — Guardrail Admission for Safety Capacity.

Multi-tenant gateway that treats **ApplyGuardrail as a finite shared safety resource** under a gateway-controlled budget \(B_g\) (not raw Bedrock capacity). Lightweight risk scores come from **MiniLM-L12-H384** (`minilm-l12-h384`). Answers come from **Llama 4 Maverick 17B**. The scheduler chooses `direct` / `strong` / `reject` and never bypasses a required strong check (fail-closed).

Locked design: [docs/experiment-design.md](docs/experiment-design.md). Knobs: [FREEZE.md](FREEZE.md).

## Roles

| Role | Where | Purpose |
| --- | --- | --- |
| G_light | MiniLM-L12-H384 (`minilm-l12-h384`) | screener / risk estimate \(q(x)\) |
| G_strong | ApplyGuardrail | authoritative safety |
| LLM | Llama 4 Maverick 17B Instruct | user response |

Paper Tenant A/B are gateway policies, not AWS accounts. v1 runs in management `646821141010`.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,g_light]"
cp .env.example .env

# Final campaign: Function URL E0a → freeze q → E1–E6 (5 reps) → one live e2e → STOP
python scripts/run_campaign.py e0a
python scripts/run_campaign.py e1-e6
python scripts/run_campaign.py e2e
```

The paper needs:

1. AWS creds that can call Bedrock (same pattern as Paper 9: local gateway → Converse / ApplyGuardrail). v1 uses management `646821141010`.
2. Llama 4 Maverick enabled. **Paper G_light is `minilm-l12-h384`** (Function URL alias), not laptop MiniLM and not Nova Micro.
3. A Guardrail ID in `.env` as `GASC_GUARDRAIL_ID`.

```bash
./scripts/create-guardrail.sh   # once; writes GASC_GUARDRAIL_ID
./scripts/smoke-bedrock.sh      # apply-guardrail + llama4-maverick

# MiniLM / Nova / Maverick via Function URL (same as bedrock-tenants smoke.sh)
ACCOUNT=a ./scripts/smoke.sh nova-micro
ACCOUNT=a ./scripts/smoke.sh llama4-maverick
ACCOUNT=a ./scripts/smoke.sh minilm-l12-h384
ACCOUNT=b ./scripts/smoke.sh minilm-l12-h384
ACCOUNT=c ./scripts/smoke.sh minilm-l12-h384
ACCOUNT=d ./scripts/smoke.sh minilm-l12-h384
```

`ACCOUNT=a|b|c|d` are AWS member accounts, not paper Tenant A/B. Management-account smoke (no `ACCOUNT=`) uses this account's `bedrock-inference-mvp` URL. MiniLM response is JSON `{"label","score","probs"}` (`harmful` / `unharmful`).

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
