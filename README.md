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

AWS `bedrock-tenant-a/b/c/d` are runtime accounts, not paper Tenant A/B.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Member stack (does **not** create the Organization or Lambda):

```bash
./scripts/tf-apply-member.sh a
./scripts/tf-apply-member.sh b
./scripts/tf-apply-member.sh c
./scripts/tf-apply-member.sh d
```

Connectivity smoke lives in [bedrock-tenants](https://github.com/taixingbi/bedrock-tenants) (`ACCOUNT=a ./scripts/smoke.sh nova-micro`). Experiment traffic is this gateway → Bedrock with role `gasc-experiment`.

## Run

Offline smoke (fixtures, no Bedrock):

```bash
gasc -c configs/smoke.yaml run --skip-llm
pytest
```

Gateway (after Terraform outputs are in `.env`):

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
# guardrail-admission-control
