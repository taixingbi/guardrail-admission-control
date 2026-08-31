# E4 safety-capacity exhaustion (frozen minilm-l12-h384 q, 5 reps)

R_gateway=3.01 rps (constant), Bg=0.4 rps, 420s/policy × 5 reps.
Suspicious/adversarial mix 5% → 50% → 5%. Offered strong demand ≈ 0.38 → 3.76 → 0.38 Bg.
Tenant A only. q=frozen_g_light. Live ApplyGuardrail, no Maverick.
Phenomenon: safety-resource exhaustion at constant gateway RPS. Do not use E4 to claim Proposed dominates.
Paper overall cells are median [p25, p75]. Do not retune τ.

## Overall (median [IQR])

| policy | G_safe | UAR | reject |
| --- | --- | --- | --- |
| always_strong | 0.286 [0.271, 0.293] | 0.128 [0.116, 0.142] | 0.875 [0.875, 0.875] |
| risk_only | 2.231 [2.224, 2.257] | 0.300 [0.288, 0.316] | 0.185 [0.172, 0.185] |
| load_aware | 2.267 [2.224, 2.283] | 0.314 [0.305, 0.316] | 0.173 [0.169, 0.188] |
| proposed | 2.269 [2.267, 2.283] | 0.326 [0.316, 0.337] | 0.166 [0.164, 0.171] |

## Per phase (rep 0)

| policy | phase | sus | offered | G_safe | UAR | reject | checked | starved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 0-120s | 5% | 0.38 Bg | 0.367 | 0.111 | 0.873 | 0.00 | 362 |
| always_strong | 120-300s | 50% | 3.76 Bg | 0.156 | 0.143 | 0.876 | 0.00 | 541 |
| always_strong | 300-420s | 5% | 0.38 Bg | 0.350 | 0.167 | 0.875 | 0.00 | 361 |
| risk_only | 0-120s | 5% | 0.38 Bg | 2.908 | 0.400 | 0.025 | 0.00 | 20 |
| risk_only | 120-300s | 50% | 3.76 Bg | 1.511 | 0.263 | 0.372 | 0.00 | 259 |
| risk_only | 300-420s | 5% | 0.38 Bg | 2.875 | 0.750 | 0.019 | 0.00 | 21 |
| load_aware | 0-120s | 5% | 0.38 Bg | 2.842 | 0.667 | 0.025 | 0.00 | 29 |
| load_aware | 120-300s | 50% | 3.76 Bg | 1.489 | 0.262 | 0.379 | 0.00 | 265 |
| load_aware | 300-420s | 5% | 0.38 Bg | 2.858 | 0.812 | 0.014 | 0.00 | 23 |
| proposed | 0-120s | 5% | 0.38 Bg | 2.833 | 0.773 | 0.014 | 0.00 | 23 |
| proposed | 120-300s | 50% | 3.76 Bg | 1.583 | 0.298 | 0.335 | 0.00 | 241 |
| proposed | 300-420s | 5% | 0.38 Bg | 2.867 | 0.750 | 0.014 | 0.00 | 18 |
