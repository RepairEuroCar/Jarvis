from reasoning.tracer import parse_tracebacks, suggest_fixes


def test_parse_traceback_extracts_info():
    text = (
        "Traceback (most recent call last):\n"
        '  File "a.py", line 1, in <module>\n'
        "    foo()\n"
        "NameError: name 'foo' is not defined\n"
    )
    result = parse_tracebacks(text)
    assert len(result) == 1
    tb = result[0]
    assert tb["frames"][0]["file"].endswith("a.py")
    assert tb["frames"][0]["line"] == 1
    assert "NameError" in tb["error"]


def test_suggest_fixes_name_error():
    msg = "NameError: name 'bar' is not defined"
    fixes = suggest_fixes(msg)
    assert any("bar" in f for f in fixes)
