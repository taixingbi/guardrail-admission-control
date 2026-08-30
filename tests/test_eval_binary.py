from gasc.eval_binary import at_threshold, average_precision, roc_auc


def test_perfect_ranking():
    y = [0, 0, 1, 1]
    s = [0.1, 0.2, 0.8, 0.9]
    assert roc_auc(y, s) == 1.0
    assert average_precision(y, s) == 1.0
    m = at_threshold(y, s, 0.5)
    assert m["unsafe_recall"] == 1.0
    assert m["fpr"] == 0.0
