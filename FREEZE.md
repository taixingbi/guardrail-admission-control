# Frozen knobs (GASC)

Fill the measured cells after E0. Do not retune \( \tau \), \( B_g \), prompts, or guardrail filters once E1 starts.

\(B_g\) is a **gateway-controlled safety budget**, not Bedrock ApplyGuardrail provider capacity. E0b measured raw ApplyGuardrail at tens of RPS; formal cells use \(B_g = 0.4\) rps to simulate an enterprise guardrail / cost quota.

| Knob | Value | Status |
| --- | --- | --- |
| G_light | `minilm-l12-h384` (paper name; Function URL, not laptop MiniLM, not Nova Micro) | locked |
| G_light train | WildGuardMix **train** only (freeze / XSTest / WildGuardTest held-out) | locked |
| G_strong | ApplyGuardrail `bklyj6c5nrb5` v1 (CLI, account `646821141010`) | locked |
| LLM | Llama 4 Maverick `us.meta.llama4-maverick-17b-instruct-v1:0` | locked |
| Runtime account | management `646821141010` (IAM `taixingbi`; member assume-role blocked) | locked for v1 |
| `GUARDRAIL_ID` | `bklyj6c5nrb5` | locked |
| `GUARDRAIL_VERSION` | `1` | locked |
| Risk threshold \( \tau \) | **0.50** global default (Tenant A 0.75 / B 0.40 stay policy knobs) | locked after E0a |
| Gateway safety budget \( B_g \) | **0.4 rps** (token-bucket; not provider capacity) | locked after E0c |
| ApplyGuardrail raw \( B_g^{raw} \) | **71.4 rps** at C=16 (E0b characterization only) | locked after E0b |
| \( R_{gateway} \) | **3.01 rps** (`0.7 × R_knee`; Maverick C\\*=2, short prompts) | locked after E0c |
| Maverick \(C^*\) | **2** (C=4 throttles / TTFT collapses) | locked after E0c |
| Maverick \(R_{knee}\) | **4.30 rps** | locked after E0c |
| Fail mode | fail-closed (E5 compares open) | locked for B4 |
| Judge (freeze only) | Claude Haiku 4.5 `us.anthropic.claude-haiku-4-5-20251001-v1:0` | locked |
| Frozen G_light \(q\) | Function URL `minilm-l12-h384` on freeze+XSTest+WildGuardTest (`results/g_light/`, `results/replay/e0a/`) | **locked** |
| Frozen prompts | **1888** (472 complete S0–S3 families) in `data/runs/main` | locked after P4 |

## Do not

- Train G_light on the P4 freeze or on WildGuardTest / XSTest.
- Change guardrail filter strengths after E0b.
- Use Nova Micro / ApplyGuardrail / Maverick labels as freeze acceptance.
- Cite laptop MiniLM (`models/g_light`, P50 6.2 ms) as paper G_light. Paper G_light is `minilm-l12-h384`.
- Cite Nova / `e*_oracle` / old `e0a_live` cells as MiniLM paper tables. Formal E0a–E6 are Function URL MiniLM, 5 reps.
- Write “Proposed guarantees safety.” The claim is policy compliance **conditional on** \(q(x)\).
- Add E7/E8 or retune \(\tau\) on XSTest / WildGuardTest.
- Map AWS `bedrock-tenant-a/b/c/d` to paper Tenant A/B.
