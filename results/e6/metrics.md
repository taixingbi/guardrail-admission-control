# E6 ablations (frozen minilm-l12-h384 q, 5 reps, E3 overload 1.5 Bg)

Same arrival process as E3 proposed overload. Fail-closed. Tenant A only. q=frozen_g_light.
Paper cells are median [p25, p75]. Full vs −NoEarlyReject is the systems headline. Do not retune τ.
P95 is safety-stage latency (scheduler + ApplyGuardrail), not user E2E.
−NoTenant applies the global τ=0.5 instead of Tenant A’s 0.75 (G_safe 2.417 vs 2.458). −NoDeadline = Full: the wait estimate is 0 or a full 2.5 s refill, so the token check rejects the same requests. NoEarlyReject P95 2002 ms is the 2 s queue timeout.

| ablation | G_safe | UAR | reject | checked | safety-stage P95 ms |
| --- | --- | --- | --- | --- | --- |
| full | 2.458 [2.358, 2.517] | 0.041 [0.035, 0.048] | 0.175 [0.155, 0.208] | 29.0 [27.0, 30.0] | 178 [178, 179] |
| no_tenant | 2.417 [2.333, 2.425] | 0.041 [0.026, 0.048] | 0.191 [0.188, 0.216] | 31.0 [27.0, 32.0] | 177 [177, 178] |
| no_deadline | 2.458 [2.358, 2.517] | 0.041 [0.035, 0.048] | 0.175 [0.155, 0.208] | 29.0 [27.0, 30.0] | 177 [177, 183] |
| no_early_reject | 2.458 [2.358, 2.517] | 0.041 [0.035, 0.048] | 0.175 [0.155, 0.208] | 39.0 [38.0, 41.0] | 2002 [2002, 2002] |
