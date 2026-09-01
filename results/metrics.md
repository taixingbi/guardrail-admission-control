# E0–E6 Function URL MiniLM campaign (paper)

Paper write-up: [summary.md](summary.md).

All headline cells below replay the **same frozen** `minilm-l12-h384` Function URL \(q\).
Do not cite Nova Micro, laptop MiniLM, or old oracle tables.

Proposed **does not guarantee GT safety**. It guarantees policy compliance **conditional on** \(q(x)\):
it never bypasses a request the policy marks as requiring strong inspection.

| exp | status | headline |
| --- | --- | --- |
| E0a | **done** Function URL MiniLM | freeze AUROC 0.986, P50/P95 524/619 ms, tenant-split 220 |
| E1 | frozen MiniLM q, 5 reps | method locked; UAR is MiniLM FN (not fail-open); Always-Strong efficiency < 1 |
| E2 | frozen MiniLM q, 5 reps | tenant isolation: Proposed 65.5%/40.3% B coverage vs load-aware 29.9%/27.1% at 90:10/70:30 |
| E3 | frozen MiniLM q, 5 reps | G_safe moves with strong-mix at fixed gateway RPS; phenomenon + MiniLM UAR |
| E4 | frozen MiniLM q, 5 reps | exhaustion at constant RPS; **not** a Proposed-dominance result |
| E5 | frozen MiniLM q, 5 reps | fail-open raises UAR without raising G_safe (use MiniLM numbers, not Nova UAR=0) |
| E6 | frozen MiniLM q, 5 reps | −NoEarlyReject adds strong work and blows P95; −NoTenant ≈ Full because Tenant A only |
| e2e | replay_q vs live_path | replay_q P50 ~584 ms is paper-comparable; live_path 6.3s/21s is Function URL on the hot path |

Bg = gateway safety budget 0.4 rps, not ApplyGuardrail provider capacity (~71 rps). No E7/E8. Write the paper.
