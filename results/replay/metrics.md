# E0–E6 freeze replay

Same knobs as the fixture scout. Prompts are the 1888-prompt P4 freeze (`data/runs/main`). Scout numbers stay in `results/eN/`.

| exp | headline on freeze |
| --- | --- |
| E0a | Live Nova Micro: AUROC 1.000, recall 1.000, FPR 0.001 at frozen τ=0.50. P95 796 ms. Do not retune. |
| E1 | Live E0a q. Proposed G_safe 2.75 / 2.78 / 2.40 at 0.5 / 1.0 / 1.5 Rg. UAR 0. |
| E2 | 120s cells, live E0a q. Proposed checks 75%/93% of B required-strong at 90:10/70:30 vs load-aware 33%/29%. |
| E3 | Live E0a q. Proposed 2.79 → 2.57 → 2.52 → 2.78. UAR 0 every phase. |
| E4 | Live E0a q. Attack floors Proposed at 1.61; recover 2.88; UAR 0 in both 5% phases. |
| E5 | Live E0a q. Fail-closed UAR 0. Fail-open UAR 0.56 / 0.66. G_safe does not rise. |
| E6 | Live E0a q. −NoTenant = Full (q bimodal). −NoEarlyReject P95 2001 ms, UAR 0.017. |
| e2e | Maverick scout. replay_q G_safe 1.93 (vs E1 2.78). live_path G_safe 0 — G_light eats the 600 ms SLO. |
