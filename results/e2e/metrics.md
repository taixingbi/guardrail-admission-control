# E2e sanity (Proposed, 1.0 Bg, 40s) — rerun 2026-11-09, guardrail wmw1sagwsxi7 v1

Tenant A SLO 600 ms unchanged. Maverick C*=2. t_llm_ms=250 (E0c TTFT P50).
Does not retune τ or Bg. E1–E6 stay Maverick-off.
replay_q uses frozen Function URL q (paper path). User E2E = frozen q + safety stage + Maverick.
live_path was not rerun: the MiniLM Function URL does not exist in account 751605536513.
The Aug 31 live_path cell used a blank guardrail ID and is archived in results/_stale_blank_guardrail_2026-08-31/e2e.

| cell | G_safe@600 | G_safe@800 | UAR | e2e P50 | e2e P95 | TTFT P95 | admitted SLO |
| --- | --- | --- | --- | --- | --- | --- | --- |
| replay_q | 1.775 | 2.525 | 0.000 (0/17) | 555 | 703 | 343 | 0.70 |

8 strong checks (all GUARDRAIL_INTERVENED), 10 deadline rejects, 0 LLM errors.
