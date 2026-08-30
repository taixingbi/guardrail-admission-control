# E6 ablations (freeze replay, E3 overload 1.5 Rg)

Same arrivals and prompts as E3 proposed. Fail-closed. Tenant A only.

| ablation | G_safe | UAR | reject | checked | starved | P50 ms | P95 ms | deadline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 2.517 | 0.000 | 0.163 | 27 | 32 | 0 | 204 | 32 |
| no_tenant | 2.517 | 0.000 | 0.163 | 27 | 32 | 0 | 205 | 32 |
| no_deadline | 2.517 | 0.000 | 0.163 | 27 | 32 | 0 | 202 | 0 |
| no_early_reject | 2.517 | 0.000 | 0.163 | 39 | 20 | 0 | 2001 | 0 |
