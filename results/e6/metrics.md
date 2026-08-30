# E6 ablations (E3 proposed overload, 1.5 Rg, 240–360 s)

Same arrivals and prompts as E3 proposed. Fail-closed. Tenant A only.

| ablation | G_safe | UAR | reject | checked | starved | P50 ms | P95 ms | deadline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 2.283 | 0.000 | 0.241 | 32 | 55 | 0 | 211 | 55 |
| no_tenant | 2.283 | 0.000 | 0.241 | 32 | 55 | 0 | 215 | 55 |
| no_deadline | 2.283 | 0.000 | 0.241 | 32 | 55 | 0 | 218 | 0 |
| no_early_reject | 2.283 | 0.000 | 0.241 | 46 | 41 | 0 | 2001 | 0 |

## Read

- Full matches the E3 proposed overload cell (\(G_{safe}=2.283\), UAR 0, 55 deadline rejects).
- −NoTenant is identical: oracle \(q\in\{0,1\}\) so tenant \(\tau\) never changes the route. A real tenant ablation needs intermediate \(q\) or a live G_light replay.
- −NoDeadline keeps the same admits/rejects; the 55 drops become `safety_floor` instead of `deadline`. With reject overflow those two knobs are substitutes.
- −NoEarlyReject still fail-closes (UAR 0) but queues: 46 checks instead of 32, and P95 latency is 2001 ms (queue timeout). Early reject is what keeps Tenant A's 600 ms SLO during overload.
