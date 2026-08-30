from gasc.external import native_gt


def test_xstest_native_labels():
    assert native_gt("xstest", "safe") == "safe"
    assert native_gt("xstest", "unsafe") == "unsafe"
    assert native_gt("xstest", "contrast_homonyms") is None


def test_wildguard_native_labels():
    assert native_gt("wildguardtest", "harmful") == "unsafe"
    assert native_gt("wildguardtest", "unharmful") == "safe"
    assert native_gt("wildguardtest", "unsafe") == "unsafe"
    assert native_gt("wildguardtest", "safe") == "safe"
    assert native_gt("wildguardtest", None) is None
