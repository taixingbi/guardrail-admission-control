# E2 multi-tenant contention (freeze replay, 120s)

Strong demand 1.3 Rg, R_gateway=3.01, 120s/cell. q=e0a_live.
Proposed reserves 40% of Rg for Tenant B. Other policies share one bucket.
`G_safe_B` is dominated by safe-direct. Isolation = checked vs starved among B required-strong.
35s freeze cell archived in `results/replay/e2_35s/`.

| policy | A:B | G_safe | G_safe_B | need_B | checked_B | starved_B | n_B_unsafe | UAR_B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| always_strong | 90%:10% | 0.175 | 0.017 | 34 | 3 | 31 | 6 | 0.000 |
| always_strong | 70%:30% | 0.125 | 0.025 | 108 | 14 | 94 | 22 | 0.000 |
| always_strong | 50%:50% | 0.133 | 0.067 | 172 | 21 | 151 | 25 | 0.000 |
| always_strong | 30%:70% | 0.158 | 0.142 | 265 | 38 | 227 | 46 | 0.022 |
| risk_only | 90%:10% | 2.492 | 0.258 | 1 | 1 | 0 | 1 | 0.000 |
| risk_only | 70%:30% | 2.608 | 0.758 | 16 | 8 | 8 | 16 | 0.000 |
| risk_only | 50%:50% | 2.525 | 1.167 | 26 | 13 | 13 | 26 | 0.000 |
| risk_only | 30%:70% | 2.550 | 1.658 | 41 | 19 | 22 | 41 | 0.000 |
| load_aware | 90%:10% | 2.392 | 0.300 | 6 | 2 | 4 | 6 | 0.000 |
| load_aware | 70%:30% | 2.433 | 0.842 | 17 | 5 | 12 | 17 | 0.000 |
| load_aware | 50%:50% | 2.450 | 1.183 | 33 | 10 | 23 | 33 | 0.000 |
| load_aware | 30%:70% | 2.542 | 1.742 | 37 | 16 | 21 | 37 | 0.000 |
| proposed | 90%:10% | 2.483 | 0.258 | 8 | 6 | 2 | 8 | 0.000 |
| proposed | 70%:30% | 2.492 | 0.717 | 14 | 13 | 1 | 13 | 0.000 |
| proposed | 50%:50% | 2.608 | 1.283 | 25 | 16 | 9 | 25 | 0.000 |
| proposed | 30%:70% | 2.525 | 1.667 | 39 | 25 | 14 | 39 | 0.000 |

## Read

Checked rate among B required-strong (`checked_B / need_B`):

| policy | 90:10 | 70:30 | 50:50 | 30:70 |
| --- | --- | --- | --- | --- |
| always_strong | 3/34 (9%) | 14/108 (13%) | 21/172 (12%) | 38/265 (14%) |
| risk_only | 1/1 | 8/16 (50%) | 13/26 (50%) | 19/41 (46%) |
| load_aware | 2/6 (33%) | 5/17 (29%) | 10/33 (30%) | 16/37 (43%) |
| proposed | **6/8 (75%)** | **13/14 (93%)** | 16/25 (64%) | 25/39 (64%) |

- B offered-strong ≈ `mix_B × 1.3 Rg` (0.05 / 0.16 / 0.26 / 0.36 rps). Reservation is 0.16 rps. At 90:10 and 70:30 the floor covers B; at 50:50 and 30:70 B's own demand overflows and leftover starves — expected, not a bug.
- Always-Strong offers ~7.5 Rg. Deadline / queue timeout starve everyone; B is not isolated.
- Risk-Only and Load-Aware share one 0.4 rps bucket. About half of B's required-strong is `strong_full` or deadline.
- `n_strong_B` stays 0 whenever ApplyGuardrail blocks and the route is rewritten to `reject`. Isolation must use `apply_guardrail_action`, not final route.
- 90:10 `n_B_unsafe` is 1–8 (risk_only drew 1). Better than the 35s 0–3, still a thin tail. 70:30 is the clean isolation contrast (13/14 vs 5/17).
- Live E0a q (1888/1888). On this freeze q is bimodal, so routing matches oracle. UAR_B is 0 except always_strong 30:70 (0.022) — ApplyGuardrail `NONE`, not a bypass.
- τ, `Rg`, and tenant knobs unchanged.
