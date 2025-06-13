from utils.linter import AstLinter


def test_detect_global_assignment(tmp_path):
    code = "x = 1\n"
    p = tmp_path / "sample.py"
    p.write_text(code, encoding="utf-8")
    linter = AstLinter()
    errors = linter.lint_paths([p])
    assert any("Global variable" in e.message for e in errors)


def test_function_too_long(tmp_path):
    lines = ["def foo():\n"] + ["    pass\n" for _ in range(20)]
    p = tmp_path / "f.py"
    p.write_text("".join(lines), encoding="utf-8")
    linter = AstLinter(max_function_lines=5)
    errors = linter.lint_paths([p])
    assert any("too long" in e.message for e in errors)


def test_top_level_call(tmp_path):
    p = tmp_path / "c.py"
    p.write_text("print('hi')\n", encoding="utf-8")
    linter = AstLinter()
    errors = linter.lint_paths([p])
    assert any("Top-level call" in e.message for e in errors)


def test_detect_eval_usage(tmp_path):
    p = tmp_path / "e.py"
    p.write_text("def foo():\n    eval('1+1')\n", encoding="utf-8")
    linter = AstLinter()
    errors = linter.lint_paths([p])
    assert any("code injection" in e.message for e in errors)
