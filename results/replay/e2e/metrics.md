# E2e Maverick scout (Proposed, 1.0 Rg, 40s)

Tenant A SLO 600 ms unchanged. Maverick C*=2. t_llm_ms=250 (E0c TTFT P50).
Does not retune τ or Rg. E1–E6 stay Maverick-off.

| cell | G_safe@600 | G_safe@800 | UAR | e2e P50 | e2e P95 | TTFT P95 | admitted SLO |
| --- | --- | --- | --- | --- | --- | --- | --- |
| replay_q | 1.925 | 2.550 | 0.000 | 555 | 672 | 376 | 0.75 |
| live_path | 0.000 | 0.100 | 0.000 | 1088 | 11817 | 1396 | 0.00 |

## Read

Proposed, 1.0 Rg, 40 s, Tenant A SLO **600 ms** (not retuned). Maverick C*=2, `max_tokens=64`. UAR 0 in both cells.

- **replay_q** (E1-comparable): G_safe 1.93 vs E1 Proposed 2.78. Adding Maverick costs ~0.85 goodput at 600 ms. E2e P50/P95 555 / 672 ms. 75% of admits still meet SLO. At Tenant B’s 800 ms, G_safe is 2.55.
- **live_path** (G_light on the critical path): G_safe@600 **0**. G_light P50/P95 361 / 580 ms already consumes the SLO before ApplyGuardrail or Maverick. E2e P50 1088 ms; P95 11.8 s is the C*=2 backlog at offered 3.01 rps. One Maverick error.
- E1–E6 `G_safe` is safety-capacity goodput with replayed q and no LLM hop. That remains the campaign metric. This scout is why: Nova Micro is not a 10 ms classifier, and stacking it with Maverick zeros Tenant A’s 600 ms SLO.
- Do not raise τ, `Rg`, or the SLO to “fix” this. A production path needs an overlapped or faster estimator, or an SLO that includes G_light.
