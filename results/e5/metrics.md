# E5 fail-open vs fail-closed (frozen minilm-l12-h384 q, 5 reps)

Proposed only. R_gateway=3.01, Bg=0.4, 60s/cell × 5 reps. q=frozen_g_light.
Fail-open disables deadline so exhaustion can bypass. Fail-closed keeps frozen B4.
Paper cells are median [p25, p75]. MiniLM is an inexpensive risk estimator, not the authority.
Fail-closed: UAR_bypass = 0 (zero scheduler-induced bypass), not a GT-safety guarantee.
Fail-open bypasses 57–62% of policy-required strong checks and raises UAR from 0.05–0.10 to 0.61–0.64
for only about 3% additional Safe Goodput.

| mode | demand | G_safe | UAR | reject | bypass/need |
| --- | --- | --- | --- | --- | --- |
| proposed_fail_closed | 1.5 Bg | 2.333 [2.200, 2.333] | 0.051 [0.029, 0.061] | 0.211 [0.200, 0.261] | 0.00 [0.00, 0.00] |
| proposed_fail_closed | 2.0 Bg | 2.200 [2.200, 2.217] | 0.095 [0.043, 0.104] | 0.239 [0.222, 0.256] | 0.00 [0.00, 0.00] |
| proposed_fail_open | 1.5 Bg | 2.350 [2.350, 2.433] | 0.611 [0.588, 0.632] | 0.083 [0.078, 0.089] | 0.57 [0.56, 0.58] |
| proposed_fail_open | 2.0 Bg | 2.267 [2.250, 2.283] | 0.636 [0.634, 0.659] | 0.089 [0.089, 0.089] | 0.62 [0.61, 0.64] |
