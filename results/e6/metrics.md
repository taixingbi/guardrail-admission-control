# E6 ablations (frozen minilm-l12-h384 q, 5 reps, E3 overload 1.5 Bg)

Same arrival process as E3 proposed overload. Fail-closed. Tenant A only. q=frozen_g_light.
Paper cells are median [p25, p75]. Full vs −NoEarlyReject is the systems headline. Do not retune τ.
P95 is **safety-stage** latency (scheduler wait + ApplyGuardrail), not user E2E
(E1–E6 have frozen q and no Maverick; MiniLM Function URL is not on the replay hot path).
Without deadline-aware early rejection the gateway does more strong-guard work without raising G_safe.
−NoTenant ≈ Full because this cell is Tenant A only (not because q is bimodal).

| ablation | G_safe | UAR | reject | checked | safety-stage P95 ms |
| --- | --- | --- | --- | --- | --- |
| full | 2.467 [2.392, 2.517] | 0.460 [0.425, 0.492] | 0.100 [0.083, 0.119] | 29.0 [27.0, 30.0] | 26 [24, 29] |
| no_tenant | 2.442 [2.375, 2.458] | 0.429 [0.411, 0.458] | 0.114 [0.102, 0.127] | 31.0 [27.0, 32.0] | 26 [25, 26] |
| no_deadline | 2.467 [2.392, 2.517] | 0.460 [0.425, 0.492] | 0.100 [0.083, 0.119] | 29.0 [27.0, 30.0] | 25 [24, 26] |
| no_early_reject | 2.467 [2.358, 2.517] | 0.635 [0.603, 0.678] | 0.069 [0.053, 0.086] | 39.0 [38.0, 41.0] | 2002 [2000, 2002] |
