from utils.solution_compare import structural_diff


def test_structural_diff_detects_change():
    a = "def foo():\n    return 1\n"
    b = "def foo():\n    return 2\n"
    diff = structural_diff(a, b)
    assert "value=Constant(value=1)" in diff
    assert "value=Constant(value=2)" in diff
