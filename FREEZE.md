# Frozen knobs (GASC)

Fill the measured cells after E0. Do not retune \( \tau \), \( R_g \), prompts, or guardrail filters once E1 starts.

| Knob | Value | Status |
| --- | --- | --- |
| G_light | Amazon Nova Micro `us.amazon.nova-micro-v1:0` | locked |
| G_light prompt | `prompts/g_light.txt` | locked |
| G_strong | ApplyGuardrail `bklyj6c5nrb5` v1 (CLI, account `646821141010`) | locked |
| LLM | Llama 4 Maverick `us.meta.llama4-maverick-17b-instruct-v1:0` | locked |
| Runtime account | management `646821141010` (IAM `taixingbi`; member assume-role blocked) | locked for v1 |
| `GUARDRAIL_ID` | `bklyj6c5nrb5` | locked |
| `GUARDRAIL_VERSION` | `1` | locked |
| Risk threshold \( \tau \) | **0.50** (scout n=64; freeze n=1888 still bimodal — 0.40/0.50/0.75 identical) | locked after E0a |
| Experimental \( R_g \) | **0.4 rps** (gateway token-bucket) | locked after E0b |
| \( R_g^{raw} \) | **71.4 rps** at C=16 (P95-stable; C=32 P95 doubles) | locked after E0b |
| \( R_{gateway} \) | **3.01 rps** (`0.7 × R_knee`; Maverick C\\*=2, short prompts) | locked after E0c |
| Maverick \(C^*\) | **2** (C=4 throttles / TTFT collapses) | locked after E0c |
| Maverick \(R_{knee}\) | **4.30 rps** | locked after E0c |
| Fail mode | fail-closed (E5 compares open) | locked for B4 |
| Judge (freeze only) | Claude Haiku 4.5 `us.anthropic.claude-haiku-4-5-20251001-v1:0` | locked |
| Frozen prompts | **1888** (472 complete S0–S3 families) in `data/runs/main` | locked after P4 |

## Do not

- Change `prompts/g_light.txt` after E0a.
- Change guardrail filter strengths after E0b.
- Use Nova Micro / ApplyGuardrail / Maverick labels as freeze acceptance.
- Put Lambda Function URL or ECS/ALB on the experiment path.
- Map AWS `bedrock-tenant-a/b/c/d` to paper Tenant A/B.
