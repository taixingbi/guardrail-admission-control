# Paper 10 experiment design (locked)

**Topic:** Multi-tenant safety-capacity scheduling for a shared Bedrock ApplyGuardrail budget  
**Setting:** opaque Bedrock backends; gateway-visible signals only (risk score, strong-guard queue, inflight, latency)

Core sentence: **ApplyGuardrail is a finite shared safety resource.** The gateway must meet tenant safety policy and latency SLOs under dynamic safety load, maximize Safe SLO-Goodput, and never bypass a required strong check.

## Roles (do not mix)

| Role | Bedrock component | Alias / ID | Purpose |
| --- | --- | --- | --- |
| G_light | Amazon Nova Micro | `nova-micro` → `us.amazon.nova-micro-v1:0` | cheap risk estimation / routing |
| G_strong | ApplyGuardrail API | `bklyj6c5nrb5` via `./scripts/create-guardrail.sh` | authoritative safety enforcement |
| LLM | Llama 4 Maverick 17B Instruct | `llama4-maverick` → `us.meta.llama4-maverick-17b-instruct-v1:0` | user response generation |

```
Request + tenant policy
        ↓
Amazon Nova Micro          (G_light)
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

Parse failure on G_light JSON → treat as REVIEW (estimator fail-closed).

Nova Micro and Maverick have separate RPM/TPM. ApplyGuardrail has its own RPS/TUPS. The scarce resource this paper schedules is **G_strong capacity**, not LLM tokens.

## AWS org (runtime, not paper tenants)

v1 runtime is management `646821141010` (IAM user `taixingbi`). Member accounts A–D exist in OU `bedrock-inference-dev` but this IAM user cannot assume `OrganizationAccountAccessRole`, so they are not on the experiment path.

Paper Tenant A/B live only in gateway policy. Do not map `bedrock-tenant-a` to Tenant A.

Create G_strong with `./scripts/create-guardrail.sh`. Experiment path is local gateway → Bedrock. No Terraform, Lambda, or ECS.

## Two-level \(R_g\)

ApplyGuardrail default quota is far above Maverick knee (~1.8 rps on this account family). Using raw API throughput as \(R_g\) would overload the LLM first.

- **E0b raw:** concurrency sweep `{1,2,4,8,16,32}` → \(R_g^{raw}\) and healthy latency. Characterization only.
- **Experimental \(R_g\):** gateway token-bucket + inflight cap, with \(R_g \ll \min(R_g^{raw}, 0.7 R_{knee}^{llm})\). Justified as a shared org safety budget.
- Real ApplyGuardrail calls still happen. The gateway only decides who may consume the budget.
- Forbidden: `quota% → change C`. Quotas are static context.

After E0 freeze \( \tau \), \( R_g \), prompts, guardrail filters, primary account. E1–E6 replay only.

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
- **B sensitive:** strong if \(q \ge 0.40\), SLO 800 ms, reserved share of \(C_g\) / \(R_g\) (policy-derived, not arrival share)

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

E0 characterize and freeze. E1–E6 replay the same 2000 prompts. Open-loop loadgen. Headlines are **E3** and **E4**.

- **E0a** Nova Micro: AUROC/AUPRC, unsafe recall, FPR, P50/P95, escalation rate. Freeze \( \tau \).
- **E0b** ApplyGuardrail concurrency sweep → \(R_g^{raw}\), then lock experimental \(R_g\).
- **E0c** Maverick knee scout (short prompts). Keep \(R_{gateway}\) below LLM knee. Not a main-text RQ.
- **E1** static strong demand \(0.25\ldots 1.50 R_g\) via S2/S3 mix; total RPS fixed.
- **E2** strong demand \(\approx 1.3 R_g\); A:B = 90:10 / 70:30 / 50:50 / 30:70.
- **E3** constant gateway RPS; mix \(0.5 \to 0.9 \to 1.5 \to 0.6 R_g\) over 480 s.
- **E4** constant RPS; suspicious/adversarial 5% → 50% → 5%.
- **E5** fail-open vs fail-closed at \(1.5 R_g\) and \(2.0 R_g\).
- **E6** ablations on an E3/E4 overload phase.

## Out of scope

Paper 7 ASR/PSR, HotpotQA, RL/WFQ, Terraform, Lambda/ECS on the hot path, retuning after freeze.
