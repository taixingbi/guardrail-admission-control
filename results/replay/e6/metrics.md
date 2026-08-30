# E6 ablations (freeze replay, E3 overload 1.5 Rg)

Same arrivals and prompts as E3 proposed. Fail-closed. Tenant A only. q=e0a_live.
Oracle cell archived in `results/replay/e6_oracle/`.

| ablation | G_safe | UAR | reject | checked | starved | P50 ms | P95 ms | deadline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 2.517 | 0.000 | 0.163 | 28 | 32 | 0 | 210 | 32 |
| no_tenant | 2.517 | 0.000 | 0.163 | 28 | 32 | 0 | 216 | 32 |
| no_deadline | 2.517 | 0.000 | 0.163 | 28 | 32 | 0 | 212 | 0 |
| no_early_reject | 2.508 | 0.017 | 0.161 | 39 | 21 | 0 | 2001 | 0 |

## Read

Live E0a q (1888/1888). Same 361-arrival E3 proposed overload (240–360 s at 1.5 Rg). Tenant A only (τ=0.75 vs global 0.50).

- **−NoTenant = Full.** Same G_safe, UAR, reject, checked/starved, deadline count. Freeze q is bimodal (0 / 0.1 / 0.95 / 1.0); nothing sits in [0.50, 0.75). Tenant τ cannot change routing on this set. That is a property of G_light, not a reason to retune τ.
- **−NoDeadline = Full admits**, reason `safety_floor` instead of `deadline`. Early reject still fires; the label changes.
- **−NoEarlyReject** queues. Checked 39 vs 28. P95 **2001 ms** (queue timeout). UAR 0.017 (one ApplyGuardrail `NONE` after a forced queue) vs Full 0. Early reject is the latency / residual-UAR knob, not tenant τ.
- Oracle archive (`e6_oracle`) matches Full / −NoTenant / −NoDeadline. −NoEarlyReject UAR was 0 there; the 0.017 is a single live-q residual, not a scheduler bypass.
- τ, `Rg`, and prompts unchanged.
