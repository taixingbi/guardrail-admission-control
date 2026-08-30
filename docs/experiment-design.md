# Paper 10 experiment design (locked)

**Topic:** Multi-tenant safety-capacity scheduling for a shared Bedrock ApplyGuardrail budget  
**Setting:** opaque Bedrock backends; gateway-visible signals only (risk score, strong-guard queue, inflight, latency)

Core sentence: **ApplyGuardrail is a finite shared safety resource.** The gateway must meet tenant safety policy and latency SLOs under dynamic safety load, maximize Safe SLO-Goodput, and never bypass a required strong check.

## Roles (do not mix)

| Role | Component | Purpose |
| --- | --- | --- |
| G_light | MiniLM-L12-H384 (`minilm-l12-h384` Function URL alias) | inexpensive risk estimate \(q(x)\in[0,1]\) |
| G_strong | Bedrock ApplyGuardrail `bklyj6c5nrb5` | authoritative safety enforcement |
| LLM | Bedrock Llama 4 Maverick 17B Instruct | user response generation |

```
Request + tenant policy
        ↓
MiniLM-L12-H384            (G_light)
        ↓
   q(x), SAFE / REVIEW
        ↓
Gateway Scheduler
   /        |         \
direct    strong     reject
   |         ↓
   |   ApplyGuardrail
   |         ↓
   └─────────┤
             ↓
Llama 4 Maverick 17B
```

Inexpensive MiniLM risk estimation gates an expensive managed safety service. \(q(x)\) is a classifier probability (continuous), not a bimodal LLM JSON score.

**Paper G_light is `minilm-l12-h384`** (bedrock-tenants Function URL alias; Lambda in-process classifier). It is **not** laptop MiniLM and **not** a Bedrock GPU / Converse FM. `models/g_light` / `GASC_GLIGHT_BACKEND=local` is a fallback only — do not cite it as G_light. Nova Micro is appendix-only (`GASC_GLIGHT_BACKEND=nova`).

The scarce resource this paper schedules is **gateway safety budget \(B_g\)** (ApplyGuardrail admissions), not LLM tokens.

## AWS org (runtime, not paper tenants)

v1 runtime is management `646821141010` (IAM user `taixingbi`). Member accounts A–D exist in OU `bedrock-inference-dev` but this IAM user cannot assume `OrganizationAccountAccessRole`, so they are not on the experiment path.

Paper Tenant A/B live only in gateway policy. Do not map `bedrock-tenant-a` to Tenant A.

Create G_strong with `./scripts/create-guardrail.sh`. E0a scores \(q(x)\) by calling `minilm-l12-h384`. E1–E6 replay those frozen scores (no Function URL on the replay hot path). Connectivity smoke may use `ACCOUNT=a|b|c|d`. Paper Tenant A/B are not those AWS accounts.

## Gateway safety budget \(B_g\) (not provider capacity)

ApplyGuardrail raw throughput on this account is tens of RPS (E0b: \(B_g^{raw} \approx 71\) rps at C=16). Using that as the experimental scarce resource would not model an enterprise guardrail / cost quota, and would also sit above the Maverick knee.

- **E0b:** raw ApplyGuardrail characterization (latency / throughput). Do not treat this as the paper’s capacity.
- **E0c:** set the **gateway-controlled safety budget** \(B_g = 0.4\) rps (token-bucket + inflight). \(B_g \ll \min(B_g^{raw}, 0.7 R_{knee}^{llm})\).
- Real ApplyGuardrail calls still happen. The gateway decides who may consume \(B_g\).
- Forbidden: `quota% → change C`. Quotas are static context.

After E0 freeze \( \tau \), \( B_g \), prompts, guardrail filters, primary account. E1–E6 replay only. Formal cells use frozen / live G_light \(q(x)\), not oracle \(\{0,1\}\).

## Dataset protocol

Generate → Validate → Freeze → Replay (same idea as GURMA P1–P6).

| Stage | Output |
| --- | --- |
| P1 | `1_seeds/seeds.jsonl` (500 intents) |
| P2 | `2_validated_seeds/validated_seeds.jsonl` |
| P3 | `3_variants/variants.jsonl` (S0–S3) |
| P4 | `4_validated_prompts/prompts.jsonl` (~2000 frozen) |
| P5 | `5_runs/run_records.jsonl` |
| P6 | `6_metrics/metrics.json` |

Variants per seed:

- **S0** clear-safe
- **S1** borderline-safe (GT=safe)
- **S2** direct-unsafe
- **S3** adversarial-unsafe (payload must remain in text)

Acceptance (independent of Nova Micro, ApplyGuardrail, Maverick):

- structural: S3 `payload_present`; S0/S1 must not contain S2/S3 wrappers; four variants share `seed_id`
- label: independent judge agrees `safe|unsafe` with the target variant
- G_light / ApplyGuardrail / Maverick outputs are **annotation only** — never `accepted`

External validation: WildGuardTest + XSTest native labels. Do not retune \( \tau \).

## Scheduler baselines

Safety floor (B4; E5 compares fail-open):

```
if policy requires ApplyGuardrail:
    capacity available → check
    capacity unavailable → reject
never: overload → bypass required guardrail
```

| ID | Inputs | Notes |
| --- | --- | --- |
| B1 Always-Strong | all → G_strong | wastes safety budget on S0 |
| B2 Risk-Only | \(q \ge \tau\) → G_strong else direct | no tenant, queue, deadline |
| B3 Load-Aware | risk + G_strong queue/load | no tenant isolation / deadline / floor reject |
| B4 Proposed | risk + tenant + capacity + queue + deadline + floor | fail-closed |

Tenants (logical):

- **A normal:** strong if \(q \ge 0.75\), SLO 600 ms, no reserved floor
- **B sensitive:** strong if \(q \ge 0.40\), SLO 800 ms, reserved share of \(B_g\) (policy-derived, not arrival share)

E6: Full / `-NoTenant` / `-NoDeadline` / `-NoEarlyReject`.

## Metrics (paper table: four only)

\[
G_{safe} = \frac{N(\text{policy compliant} \land \text{safe} \land \text{served} \land \text{latency} \le SLO)}{T}
\]

Rejects are policy-compliant and safe when they avoid admitting GT-unsafe traffic, but they are **not** goodput.

- **policy compliant:** required strong was checked or the request was rejected; bypass is non-compliant
- **safe:** GT-unsafe must not reach Maverick; reject is safe but not goodput
- **Unsafe Admission Rate:** GT-unsafe admitted to Maverick / GT-unsafe
- **Critical-tenant SLO attainment:** Tenant B among requests that should be served
- **Guardrail capacity efficiency:** policy-required ApplyGuardrail occupancy / all ApplyGuardrail occupancy

## Campaign

E0 characterize and freeze. E1–E6 keep the same frame. Formal cells use frozen / live \(q(x)\). Headlines: **E2** (tenant policy), **E5** (fail-closed), **E6** (early reject).

- **E0a** Paper G_light = `minilm-l12-h384`. Re-score freeze + XSTest + WildGuardTest via Function URL (`python scripts/score_g_light.py`). Keep \(\tau=0.50\). Do **not** cite laptop MiniLM AUROC 0.985 / P50–P95 6.2/7.4 ms as the paper cell (appendix only). After re-score, compare the \(0.40\le q<0.75\) band; re-run E1–E6 only if that band moves.
- **E0b** Raw ApplyGuardrail characterization (do not rerun).
- **E0c** Define gateway safety budget \(B_g = 0.4\) rps; Maverick knee sets \(R_{gateway}\).
- **E1** Static safety-budget sweep. Keep until E0a `minilm-l12-h384` \(q\) is frozen.
- **E2** Multi-tenant contention (`minilm-l12-h384` \(q\), 5 reps). Split-band: Proposed A 100% direct, B 100% strong. Isolation numbers below are from laptop MiniLM \(q\) — replace after E0a re-score. Do not retune \(\tau\) or \(B_g\).
- **E3** Dynamic safety demand. Update: live \(q(x)\), 5 reps. Hypothesis: Proposed **preserves the safety floor with bounded goodput cost** (not “highest throughput”).
- **E4** Tenant-targeted safety-resource exhaustion. Update: constant total RPS, risky mix explodes strong-guard demand; optional A-flood / B-normal isolation.
- **E5** Fail-open vs fail-closed. Keep + 5 reps.
- **E6** Deadline / early-reject ablation. Keep + 5 reps. Full vs −NoEarlyReject is the systems headline.

## Out of scope

Paper 7 ASR/PSR, HotpotQA, RL/WFQ, Terraform, ECS/ALB as the gateway, retuning after freeze. G_light’s MiniLM is the Function URL alias `minilm-l12-h384`, not a laptop-only runtime.
