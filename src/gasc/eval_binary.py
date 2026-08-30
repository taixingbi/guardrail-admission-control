from __future__ import annotations


def roc_auc(y_true: list[int], scores: list[float]) -> float | None:
    pos = [s for s, y in zip(scores, y_true) if y]
    neg = [s for s, y in zip(scores, y_true) if not y]
    if not pos or not neg:
        return None
    wins = 0.0
    ties = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1
            elif p == n:
                ties += 1
    return (wins + 0.5 * ties) / (len(pos) * len(neg))


def average_precision(y_true: list[int], scores: list[float]) -> float | None:
    paired = sorted(zip(scores, y_true), key=lambda x: x[0], reverse=True)
    n_pos = sum(y_true)
    if n_pos == 0:
        return None
    hit = 0
    ap = 0.0
    for i, (_, y) in enumerate(paired, start=1):
        if not y:
            continue
        hit += 1
        ap += hit / i
    return ap / n_pos


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    frac = k - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


def at_threshold(y_true: list[int], scores: list[float], tau: float) -> dict[str, float]:
    pred = [1 if s >= tau else 0 for s in scores]
    tp = sum(1 for y, p in zip(y_true, pred) if y and p)
    fp = sum(1 for y, p in zip(y_true, pred) if (not y) and p)
    tn = sum(1 for y, p in zip(y_true, pred) if (not y) and (not p))
    fn = sum(1 for y, p in zip(y_true, pred) if y and (not p))
    n_pos = tp + fn
    n_neg = fp + tn
    return {
        "tau": tau,
        "unsafe_recall": (tp / n_pos) if n_pos else 0.0,
        "fpr": (fp / n_neg) if n_neg else 0.0,
        "precision": (tp / (tp + fp)) if (tp + fp) else 0.0,
        "escalation_rate": sum(pred) / max(len(pred), 1),
        "youden": ((tp / n_pos) if n_pos else 0.0) - ((fp / n_neg) if n_neg else 0.0),
    }


def sweep_tau(y_true: list[int], scores: list[float]) -> tuple[list[dict[str, float]], dict[str, float]]:
    grid = [i / 20 for i in range(1, 20)]
    rows = [at_threshold(y_true, scores, tau) for tau in grid]
    best = max(rows, key=lambda r: (r["youden"], r["unsafe_recall"], -r["fpr"]))
    return rows, best
