# E5 fail-open vs fail-closed (frozen minilm-l12-h384 q, 5 reps)

Proposed only. R_gateway=3.01, Bg=0.4, 60s/cell × 5 reps. q=frozen_g_light.
Fail-open disables deadline so exhaustion can bypass. Fail-closed keeps frozen B4.
Paper cells are median [p25, p75]. MiniLM is an inexpensive risk estimator, not the authority.
Fail-closed: UAR_bypass = 0 (zero scheduler-induced bypass), not a GT-safety guarantee.
Fail-open admits all GT-unsafe in these cells and bypasses a large share of required strong checks
for only ~3% additional Safe Goodput. Residual fail-closed UAR is MiniLM FN and/or G_strong miss.
n_checked rebuilt from jsonl via applied_strong (formal records store action=None).

| mode | demand | G_safe | UAR | light | strong | bypass | reject | bypass/need | checked | starved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proposed_fail_closed | 1.5 Bg | 2.333 [2.200, 2.367] | 0.436 [0.429, 0.457] | 0.051 [0.029, 0.061] | 0.385 [0.367, 0.400] | 0.000 [0.000, 0.000] | 0.128 [0.122, 0.161] | 0.00 [0.00, 0.00] | 15.0 [15.0, 18.0] | 23.0 [22.0, 29.0] |
| proposed_fail_closed | 2.0 Bg | 2.200 [2.200, 2.267] | 0.458 [0.370, 0.476] | 0.095 [0.043, 0.104] | 0.326 [0.319, 0.354] | 0.000 [0.000, 0.000] | 0.144 [0.139, 0.167] | 0.00 [0.00, 0.00] | 16.0 [16.0, 17.0] | 26.0 [25.0, 30.0] |
| proposed_fail_open | 1.5 Bg | 2.400 [2.367, 2.433] | 1.000 [1.000, 1.000] | 0.056 [0.056, 0.059] | 0.394 [0.389, 0.412] | 0.529 [0.528, 0.556] | 0.000 [0.000, 0.000] | 0.57 [0.56, 0.58] | 15.0 [14.0, 16.0] | 20.0 [19.0, 20.0] |
| proposed_fail_open | 2.0 Bg | 2.267 [2.250, 2.300] | 1.000 [1.000, 1.000] | 0.057 [0.024, 0.068] | 0.364 [0.341, 0.366] | 0.591 [0.549, 0.610] | 0.000 [0.000, 0.000] | 0.62 [0.61, 0.64] | 16.0 [16.0, 16.0] | 27.0 [26.0, 28.0] |
