from gasc.eval_binary import at_threshold, average_precision, roc_auc
from gasc.report import fmt_stat, stat_pack


def test_perfect_ranking():
    y = [0, 0, 1, 1]
    s = [0.1, 0.2, 0.8, 0.9]
    assert roc_auc(y, s) == 1.0
    assert average_precision(y, s) == 1.0
    m = at_threshold(y, s, 0.5)
    assert m["unsafe_recall"] == 1.0
    assert m["fpr"] == 0.0


def test_stat_pack_median_iqr():
    p = stat_pack([1.0, 2.0, 3.0, 4.0, 5.0])
    assert p["n"] == 5
    assert p["mean"] == 3.0
    assert p["median"] == 3.0
    assert p["p25"] == 2.0
    assert p["p75"] == 4.0
    assert fmt_stat(p) == "3.000 [2.000, 4.000]"
    assert fmt_stat({"median": None}) == "—"
