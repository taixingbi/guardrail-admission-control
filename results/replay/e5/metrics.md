# E5 fail-open vs fail-closed (frozen minilm-l12-h384 q, 5 reps)

Proposed only. R_gateway=3.01, Bg=0.4, 60s/cell × 5 reps. q=frozen_g_light.
Fail-open disables deadline so exhaustion can bypass. Fail-closed keeps frozen B4.
Paper cells are median [p25, p75]. MiniLM is a screener, not the authority. Do not retune τ.
Fail-open raises UAR without raising Safe Goodput. Residual fail-closed UAR is MiniLM FN, not bypass.

| mode | demand | G_safe | UAR | reject | bypass/need |
| --- | --- | --- | --- | --- | --- |
| proposed_fail_closed | 1.5 Bg | 2.333 [2.200, 2.367] | 0.436 [0.429, 0.457] | 0.128 [0.122, 0.161] | 0.00 [0.00, 0.00] |
| proposed_fail_closed | 2.0 Bg | 2.200 [2.200, 2.267] | 0.458 [0.370, 0.476] | 0.144 [0.139, 0.167] | 0.00 [0.00, 0.00] |
| proposed_fail_open | 1.5 Bg | 2.400 [2.367, 2.433] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.57 [0.56, 0.58] |
| proposed_fail_open | 2.0 Bg | 2.267 [2.250, 2.300] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.62 [0.61, 0.64] |
