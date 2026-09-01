# E2e sanity (Proposed, 1.0 Bg, 40s)

Tenant A SLO 600 ms unchanged. Maverick C*=2. t_llm_ms=250 (E0c TTFT P50).
Does not retune τ or Bg. E1–E6 stay Maverick-off.
replay_q uses frozen Function URL q (paper-comparable path). live_path scores every request
via Function URL MiniLM (E0a P50 ~524 ms) and is not the 600 ms SLO architecture number.

| cell | G_safe@600 | G_safe@800 | UAR | e2e P50 | e2e P95 | TTFT P95 | admitted SLO |
| --- | --- | --- | --- | --- | --- | --- | --- |
| replay_q | 1.475 | 2.500 | 0.412 | 584 | 735 | 348 | 0.60 |
| live_path | 0.000 | 0.000 | 0.400 | 6307 | 21160 | 1433 | 0.00 |
