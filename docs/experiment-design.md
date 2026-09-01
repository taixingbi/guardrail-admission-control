# Paper 10 experiment design (locked)

**Topic:** Multi-tenant safety-capacity scheduling for a shared Bedrock ApplyGuardrail budget  
**Setting:** opaque Bedrock backends; gateway-visible signals only (risk score, strong-guard queue, inflight, latency)

Core sentence: **ApplyGuardrail is a finite shared safety resource.** The gateway must meet tenant safety policy and latency SLOs under dynamic safety load, maximize Safe SLO-Goodput, and never bypass a required strong check. Required is defined by the gateway risk signal \(q(x)\) and tenant \(\tau\), not by ground-truth labels.

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

**Paper G_light is `minilm-l12-h384`** (bedrock-tenants Function URL alias; Lambda in-process classifier). It is **not** laptop MiniLM and **not** a Bedrock GPU / Converse FM. MiniLM is a **lightweight classifier / inexpensive risk estimator** (model size and role), not a low-latency guardrail — Function URL P50/P95 is ~524/619 ms, which is higher than ApplyGuardrail at C≤16. ApplyGuardrail is the **authoritative** strong check. Do not retune \(\tau\) on WildGuardTest / XSTest.

`models/g_light` / `GASC_GLIGHT_BACKEND=local` is a fallback only — do not cite it as G_light. Nova Micro is appendix-only (`GASC_GLIGHT_BACKEND=nova`).

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

- **policy compliant:** required strong was checked or the request was rejected; bypass is non-compliant. This is compliance **given** \(q(x)\), not GT safety.
- **safe:** GT-unsafe must not reach Maverick; reject is safe but not goodput
- **Unsafe Admission Rate:** GT-unsafe admitted to the LLM path / GT-unsafe. Decompose as \(UAR = UAR_{light} + UAR_{strong} + UAR_{bypass}\):
  - \(UAR_{light}\): \(q\) below risk \(\tau\), direct, admitted (MiniLM FN / below-threshold)
  - \(UAR_{strong}\): ApplyGuardrail occupied, did not block, admitted (G_strong miss)
  - \(UAR_{bypass}\): policy required strong, scheduler bypassed, admitted
  Always-Strong UAR is G_strong miss, not MiniLM FN. Fail-closed Proposed has \(UAR_{bypass}=0\); residual UAR may still include MiniLM FN and G_strong miss.
- **Critical-tenant SLO attainment:** Tenant B among requests that should be served
- **Guardrail capacity efficiency:** risk-required ApplyGuardrail occupancy / all ApplyGuardrail occupancy. Risk-required means \(q \ge \tau\) (tenant \(\tau\) for Proposed; else global \(\tau=0.50\)). Always-Strong occupancy with \(q < \tau\) is waste, so its efficiency is not identically 1.
- **Safety-stage / controller-path latency:** scheduler wait + ApplyGuardrail. This is what E1–E6 P95 measures (frozen \(q\), no Maverick, MiniLM Function URL not on the replay hot path). User E2E = G_light + safety stage + Maverick. Safe SLO-Goodput in E1–E6 is SLO-compliant goodput under the modeled controller deadline, not a claimed real-user E2E SLO.

## Campaign status (locked)

No E7/E8. Architecture is frozen. Paper G_light is Function URL `minilm-l12-h384`.

**Claim (do not overstate):** Proposed guarantees **policy compliance conditional on** \(q(x)\): it never bypasses a request the policy marks as requiring strong inspection. Fail-closed means **zero scheduler-induced bypass**. Residual UAR is MiniLM FN and/or ApplyGuardrail miss, not fail-open. Do not write “Proposed guarantees safety” or “residual UAR is MiniLM FN” for all policies.

| Cell | Status |
| --- | --- |
| E0a | **Done.** Function URL MiniLM on freeze + XSTest + WildGuardTest. Freeze AUROC 0.986, P50/P95 524/619 ms. Split-band \(0.40\le q<0.75\) = **220 across scored evaluation sets** (freeze 38 + XSTest 40 + WildGuard 142), not 220 in freeze alone. Same \(q\) as laptop MiniLM; latency is the endpoint. |
| E0b / E0c | Do not rerun. \(B_g=0.4\), \(R_{gateway}=3.01\) locked. |
| E1–E6 | **Done.** Same frozen Function URL \(q\), 5 reps, median [p25, p75]. No Function URL on the replay hot path. |
| E2 | Paper-level tenant result (split-band 220; Proposed A 100% direct / B 100% strong; B coverage 65.5%/40.3% vs load-aware 29.9%/27.1% at 90:10 / 70:30). |
| E4 | Phenomenon only (exhaustion at constant RPS). Do not claim Proposed dominates. |
| E5 / E6 | Mechanism holds on MiniLM \(q\). Cite these MiniLM numbers, not old Nova UAR=0 tables. |
| Live e2e | `replay_q` (P50 ~584 ms) is paper-comparable. `live_path` (P50 6.3s / P95 21s) puts Function URL MiniLM on every request and is **not** the 600 ms SLO architecture number. |
| Appendix | Nova Micro (`GASC_GLIGHT_BACKEND=nova`) is opt-in only. Oracle / laptop MiniLM / old scout folders were removed from `results/`. Do not mix with paper tables. |

```
python3 scripts/run_campaign.py          # already run; do not retune
python3 scripts/refresh_replay_metrics.py  # rebuild md/json from jsonl (no AWS)
```

After this pass: do not change model, \(\tau\), or datasets. **Write the paper.**

## Out of scope

Paper 7 ASR/PSR, HotpotQA, RL/WFQ, Terraform, ECS/ALB as the gateway, retuning \(\tau\) after freeze, extra experiments E7/E8.
