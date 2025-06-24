import scripts.generate_core_tests as gct


def test_parse_added_functions():
    diff = """
@@
+def foo():
+    pass
@@
+async def bar():
+    pass
"""
    assert gct.parse_added_functions(diff) == ["foo", "bar"]


def test_main_calls_generator(monkeypatch):
    outputs = {}

    def fake_run(cmd):
        if cmd[:3] == ["git", "diff", "--name-only"]:
            return "core/x.py\nnotcore.txt\n"
        if cmd[:3] == ["git", "diff", "HEAD~1"]:
            return "+def foo():\n    pass\n"
        return ""

    monkeypatch.setattr(gct, "run", fake_run)

    def fake_gen(path, out):
        outputs[path] = out
        return ["tests/generated/test_foo.py"]

    monkeypatch.setattr(gct, "generate_autotests", fake_gen)

    result = gct.main("HEAD~1")
    assert outputs == {"core/x.py": "tests/generated"}
    assert result == ["tests/generated/test_foo.py"]
