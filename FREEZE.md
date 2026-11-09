# Frozen knobs (GASC)

Fill the measured cells after E0. Do not retune \( \tau \), \( B_g \), prompts, or guardrail filters once E1 starts.

\(B_g\) is a **gateway-controlled safety budget**, not Bedrock ApplyGuardrail provider capacity. E0b measured raw ApplyGuardrail at tens of RPS; formal cells use \(B_g = 0.4\) rps to simulate an enterprise guardrail / cost quota.

| Knob | Value | Status |
| --- | --- | --- |
| G_light | `minilm-l12-h384` (paper name; Function URL, not laptop MiniLM, not Nova Micro) | locked |
| G_light train | WildGuardMix **train** only (freeze / XSTest / WildGuardTest held-out) | locked |
| G_strong | ApplyGuardrail `gasc-strong` `wmw1sagwsxi7` v1 (account `751605536513`, us-east-1), re-created 2026-11-08 from `scripts/guardrail-content-policy.json`. Original `bklyj6c5nrb5` v1 (account `646821141010`) is unreachable; see Rerun below | locked |
| LLM | Llama 4 Maverick `us.meta.llama4-maverick-17b-instruct-v1:0` | locked |
| Runtime account | `751605536513` for E0b–E6 + e2e rerun (2026-11-08/09). E0a, E0c, freeze ran in `646821141010` | locked |
| `GUARDRAIL_ID` | `wmw1sagwsxi7` (was `bklyj6c5nrb5`) | locked |
| `GUARDRAIL_VERSION` | `1` | locked |
| Risk threshold \( \tau \) | **0.50** global default (Tenant A 0.75 / B 0.40 stay policy knobs) | locked after E0a |
| Gateway safety budget \( B_g \) | **0.4 rps** (token-bucket; not provider capacity) | locked after E0c |
| ApplyGuardrail raw \( B_g^{raw} \) | **101.67 rps** at C=16 (E0b rerun 2026-11-08; was 71.4 with the old guardrail) | locked after E0b |
| \( R_{gateway} \) | **3.01 rps** (`0.7 × R_knee`; Maverick C\\*=2, short prompts) | locked after E0c |
| Maverick \(C^*\) | **2** (C=4 throttles / TTFT collapses) | locked after E0c |
| Maverick \(R_{knee}\) | **4.30 rps** | locked after E0c |
| Fail mode | fail-closed (E5 compares open) | locked for B4 |
| Judge (freeze only) | Claude Haiku 4.5 `us.anthropic.claude-haiku-4-5-20251001-v1:0` | locked |
| Frozen G_light \(q\) | Function URL `minilm-l12-h384` on freeze+XSTest+WildGuardTest (`results/e0a/`) | **locked** |
| Frozen prompts | **1888** (472 complete S0–S3 families) in `data/runs/main` | locked after P4 |

## Rerun (2026-11-08/09)

The Aug 30–31 2026 E1–E6 campaign ran with `GASC_GUARDRAIL_ID` blank: ApplyGuardrail returned in ~20 ms with no `action`, so no strong check ever executed (0 interventions in ~10k "checks"). Those results are archived in `results/_stale_blank_guardrail_2026-08-31/` and must not be cited.

E0b, E1–E6 and e2e `replay_q` were rerun against `wmw1sagwsxi7` v1 with τ, B_g, R_gateway, prompts, frozen q and filter strengths unchanged. Provenance: `results/rerun_provenance/`. e2e `live_path` was not rerun (MiniLM Function URL is not deployed in `751605536513`).

Guards added so this cannot recur: `bedrock_session()` refuses a blank ID or DRAFT version and preflights one ApplyGuardrail call; a strong check without a valid verdict raises `GuardrailError`; `aggregate()` rejects strong-routed records without a verdict.

## Do not

- Train G_light on the P4 freeze or on WildGuardTest / XSTest.
- Change guardrail filter strengths after E0b.
- Run E1–E6 with `GASC_GUARDRAIL_ID` unset or a DRAFT version.
- Use Nova Micro / ApplyGuardrail / Maverick labels as freeze acceptance.
- Cite laptop MiniLM (`models/g_light`, P50 6.2 ms) as paper G_light. Paper G_light is `minilm-l12-h384`.
- Cite Nova / oracle / laptop MiniLM / old scout cells as MiniLM paper tables. Formal E0a–E6 are Function URL MiniLM, 5 reps.
- Write “Proposed guarantees safety.” The claim is policy compliance **conditional on** \(q(x)\).
- Add E7/E8 or retune \(\tau\) on XSTest / WildGuardTest.
- Map AWS `bedrock-tenant-a/b/c/d` to paper Tenant A/B.
