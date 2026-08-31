# E6 ablations (frozen minilm-l12-h384 q, 5 reps, E3 overload 1.5 Rg)

Same arrival process as E3 proposed overload. Fail-closed. Tenant A only. q=frozen_g_light.
Paper cells are median [p25, p75]. Full vs −NoEarlyReject is the systems headline. Do not retune τ.

| ablation | G_safe | UAR | reject |
| --- | --- | --- | --- |
| full | 2.467 [2.392, 2.517] | 0.460 [0.425, 0.492] | 0.100 [0.083, 0.119] |
| no_tenant | 2.442 [2.375, 2.458] | 0.429 [0.411, 0.458] | 0.114 [0.102, 0.127] |
| no_deadline | 2.467 [2.392, 2.517] | 0.460 [0.425, 0.492] | 0.100 [0.083, 0.119] |
| no_early_reject | 2.467 [2.358, 2.517] | 0.635 [0.603, 0.678] | 0.069 [0.053, 0.086] |
