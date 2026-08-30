# E4 safety-capacity exhaustion

R_gateway=3.01 rps (constant), Rg=0.4 rps, 420s/policy.
Suspicious/adversarial mix 5% → 50% → 5%. Offered strong demand ≈ 0.38 → 3.76 → 0.38 Rg.
Tenant A only. Injected oracle q. Live ApplyGuardrail, no Maverick.

## Per phase

| policy | phase | sus | offered | G_safe | UAR | reject | checked | starved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 0-120s | 5% | 0.38 Rg | 0.158 | 0.053 | 0.942 | 0.13 | 316 |
| always_strong | 120-300s | 50% | 3.76 Rg | 0.106 | 0.007 | 0.961 | 0.12 | 474 |
| always_strong | 300-420s | 5% | 0.38 Rg | 0.183 | 0.000 | 0.939 | 0.12 | 316 |
| risk_only | 0-120s | 5% | 0.38 Rg | 2.858 | 0.000 | 0.052 | 0.63 | 7 |
| risk_only | 120-300s | 50% | 3.76 Rg | 1.511 | 0.004 | 0.495 | 0.22 | 211 |
| risk_only | 300-420s | 5% | 0.38 Rg | 2.858 | 0.056 | 0.047 | 0.78 | 4 |
| load_aware | 0-120s | 5% | 0.38 Rg | 2.933 | 0.000 | 0.028 | 0.80 | 2 |
| load_aware | 120-300s | 50% | 3.76 Rg | 1.556 | 0.004 | 0.481 | 0.23 | 201 |
| load_aware | 300-420s | 5% | 0.38 Rg | 2.858 | 0.056 | 0.047 | 0.72 | 5 |
| proposed | 0-120s | 5% | 0.38 Rg | 2.858 | 0.000 | 0.052 | 0.74 | 5 |
| proposed | 120-300s | 50% | 3.76 Rg | 1.544 | 0.011 | 0.481 | 0.22 | 204 |
| proposed | 300-420s | 5% | 0.38 Rg | 2.892 | 0.000 | 0.039 | 0.79 | 3 |

## Overall

| policy | G_safe | UAR | reject | checked | starved |
| --- | --- | --- | --- | --- | --- |
| always_strong | 0.143 | 0.010 | 0.949 | 0.12 | 1106 |
| risk_only | 2.281 | 0.007 | 0.241 | 0.27 | 222 |
| load_aware | 2.321 | 0.007 | 0.227 | 0.28 | 208 |
| proposed | 2.305 | 0.010 | 0.232 | 0.28 | 212 |

## Read

- Gateway RPS never changes. The 50% spike is safety-capacity exhaustion, not LLM overload.
- Always-Strong stays near \(G_{safe}\approx 0.11\) in the attack: the 0.4 rps budget is spent on a flood of strong checks and benign traffic is queued/rejected.
- Risk-Only / Load-Aware / Proposed drop to \(G_{safe}\approx 1.51\)–\(1.56\) in the attack — about the 50% benign-direct floor — then recover to \(\approx 2.86\) when the mix returns to 5%.
- Bypass is 0. Residual attack UAR (0.4–1.1%) is ApplyGuardrail `NONE` on weak S2, not a scheduler skip. Proposed is the only policy with UAR = 0 in both 5% phases.

## G_safe time series (10 s bins)

- **always_strong:** `0.30 0.10 0.20 0.20 0.20 0.30 0.10 0.20 0.00 0.00 0.20 0.10 0.10 0.10 0.10 0.10 0.10 0.30 0.10 0.20 0.00 0.10 0.30 0.00 0.00 0.10 0.10 0.00 0.10 0.10 0.00 0.10 0.20 0.00 0.30 0.10 0.30 0.20 0.40 0.30 0.10 0.20`
- **risk_only:** `3.00 2.40 2.90 2.90 2.80 2.80 3.00 3.00 2.80 2.80 2.90 3.00 1.10 1.50 1.50 1.50 1.70 1.80 1.70 1.60 1.60 1.20 1.50 1.50 1.20 1.70 1.30 1.40 1.60 1.80 2.90 2.90 2.70 2.70 2.90 2.90 2.90 2.90 2.90 2.80 3.00 2.80`
- **load_aware:** `3.00 3.00 2.80 3.00 3.00 2.90 2.70 2.90 2.90 3.00 3.10 2.90 1.80 1.40 1.50 1.10 1.30 1.50 2.00 1.90 1.30 1.80 1.40 1.90 1.30 1.60 1.60 1.30 1.60 1.70 2.90 3.00 2.80 2.70 2.80 3.00 2.80 2.70 2.90 3.00 2.90 2.80`
- **proposed:** `2.70 2.80 3.00 3.00 2.80 2.90 2.90 2.90 2.90 3.00 2.80 2.60 1.80 1.60 2.10 1.50 1.70 1.30 1.80 2.00 2.00 1.60 1.40 1.30 0.70 1.60 1.20 1.80 1.30 1.10 3.00 3.00 3.00 2.90 3.00 2.90 2.70 2.70 2.80 2.90 2.90 2.90`
