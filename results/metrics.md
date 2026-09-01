# E0–E6 Function URL MiniLM campaign (paper)

Paper write-up: [summary.md](summary.md).

All headline cells below replay the **same frozen** `minilm-l12-h384` Function URL \(q\).
Do not cite Nova Micro, laptop MiniLM, or old oracle tables.

Proposed **does not guarantee GT safety**. It guarantees policy compliance **conditional on** \(q(x)\):
it never bypasses a request the policy marks as requiring strong inspection.
Fail-closed means **zero scheduler-induced bypass** (\(UAR_{bypass}=0\)), not MiniLM-FN-only residual UAR.

E1–E6 P95 is **safety-stage / controller-path** latency (scheduler + ApplyGuardrail), not user E2E.
MiniLM is an inexpensive risk estimator, not a low-latency guardrail.

| exp | status | headline |
| --- | --- | --- |
| E0a | **done** Function URL MiniLM | freeze AUROC 0.986, P50/P95 524/619 ms; 220 split-band across freeze+XSTest+WildGuardTest |
| E1 | frozen MiniLM q, 5 reps | Always-Strong wastes \(B_g\); UAR split (Always-Strong UAR is G_strong miss) |
| E2 | frozen MiniLM q, 5 reps | tenant isolation: Proposed 65.5%/40.3% B coverage vs load-aware 29.9%/27.1% at 90:10/70:30 |
| E3 | frozen MiniLM q, 5 reps | dynamic-load robustness at fixed RPS; not Proposed-dominance |
| E4 | frozen MiniLM q, 5 reps | exhaustion at constant RPS; checked/starved from applied_strong; not dominance |
| E5 | frozen MiniLM q, 5 reps | fail-open: UAR_bypass ↑, ~3% extra G_safe; fail-closed UAR_bypass = 0 |
| E6 | frozen MiniLM q, 5 reps | −NoEarlyReject: +strong work, safety-stage P95 ~77×, same G_safe |
| e2e | replay_q vs live_path | replay_q P50 ~584 ms is paper-comparable; live_path 6.3s/21s is Function URL on the hot path |

Bg = gateway safety budget 0.4 rps, not ApplyGuardrail provider capacity (~71 rps). No E7/E8. Write the paper.
