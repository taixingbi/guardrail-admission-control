# E0–E6 Function URL MiniLM campaign (paper)

Paper write-up: [summary.md](summary.md).

All headline cells below replay the **same frozen** `minilm-l12-h384` Function URL \(q\).
Do not cite Nova Micro, laptop MiniLM, or old oracle tables.

Proposed **does not guarantee GT safety**. It guarantees policy compliance **conditional on** \(q(x)\):
it never bypasses a request the policy marks as requiring strong inspection.
Fail-closed means **zero scheduler-induced bypass** (\(UAR_{bypass}=0\)), not MiniLM-FN-only residual UAR.

E1–E6 P95 is **safety-stage / controller-path** latency (scheduler + ApplyGuardrail), not user E2E.
MiniLM is an inexpensive risk estimator, not a low-latency guardrail.

Rerun 2026-11-08/09 with live guardrail `wmw1sagwsxi7` v1. The Aug 30–31 campaign (blank guardrail ID) is archived and must not be cited.

| exp | status | headline |
| --- | --- | --- |
| E0a | done (unchanged) | freeze AUROC 0.986, P50/P95 524/619 ms |
| E0b | rerun | B_g^raw 101.67 rps at C=16, P50/P95 141/231 ms |
| E1 | rerun, 5 reps | Always-Strong G_safe 0.18 (rejects ~94%); adaptive ~2.5; UAR = MiniLM FN only |
| E2 | rerun, 5 reps | B coverage 65.5/40.3/30.9/25.2% vs 29.9/27.1/25.6/22.0%; UAR_B lower at 70:30–30:70 |
| E3 | rerun, 5 reps | Proposed G_safe 2.642 (best), reject 0.117 |
| E4 | rerun, 5 reps | exhaustion at constant RPS; burst tied; Proposed UAR slightly higher |
| E5 | rerun, 5 reps | fail-open UAR 0.61–0.64 vs 0.05–0.10, bypass 57–62%, ≤3% G_safe |
| E6 | rerun, 5 reps | −NoEarlyReject: +34% strong work, safety-stage P95 178 → 2002 ms (×11), same G_safe |
| e2e | replay_q rerun | E2E P50/P95 555/703 ms, UAR 0/17; live_path not rerun |

Bg = gateway safety budget 0.4 rps, not ApplyGuardrail provider capacity (~102 rps). No E7/E8.
