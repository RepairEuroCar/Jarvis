import asyncio

import pytest

from command_dispatcher import default_dispatcher
from jarvis.memory.manager import MemoryManager
from modules import executor
from utils.linter import AstLinter, LintError


@pytest.mark.asyncio
async def test_executor_run(monkeypatch):
    calls = []

    async def fake_exec(*args, **kwargs):
        calls.append(args)

        class Proc:
            returncode = 0

            async def communicate(self):
                if "pytest" in args:
                    return b"3 passed, 1 failed", b""
                if "ruff" in args:
                    return b"sample.py:1:1 F401 unused import", b""
                return b"", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    result = await executor.run(".")
    assert result["tests"]["passed"] == 3
    assert result["tests"]["failed"] == 1
    assert len(result["lint"]["warnings"]) == 1
    assert "F401" in result["lint"]["warnings"][0]
    assert any("pytest" in c for c in calls)
    assert any("ruff" in c for c in calls)


@pytest.mark.asyncio
async def test_executor_run_ast_fallback(monkeypatch):
    async def fake_exec(*args, **kwargs):
        if "pytest" in args:

            class Proc:
                returncode = 0

                async def communicate(self):
                    return b"1 passed", b""

            return Proc()
        raise FileNotFoundError

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    def fake_lint(self, paths):
        return [LintError(filepath="a.py", lineno=1, message="bad")]

    monkeypatch.setattr(AstLinter, "lint_paths", fake_lint)

    result = await executor.run(".")
    assert result["tests"]["passed"] == 1
    assert result["tests"]["failed"] == 0
    assert result["lint"]["warnings"] == ["a.py:1: bad"]


@pytest.mark.asyncio
async def test_executor_records_traceback(monkeypatch):
    async def fake_exec(*args, **kwargs):
        if "pytest" in args:

            class Proc:
                returncode = 1

                async def communicate(self):
                    tb = (
                        "Traceback (most recent call last):\n"
                        '  File "t.py", line 1, in <module>\n'
                        "    foo()\n"
                        "NameError: name 'foo' is not defined\n"
                        "1 failed\n"
                    )
                    return tb.encode(), b""

            return Proc()
        raise FileNotFoundError

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    def fake_lint(self, paths):
        return []

    monkeypatch.setattr(AstLinter, "lint_paths", fake_lint)

    result = await executor.run(".")
    assert result["tests"]["failed"] == 1
    assert result["errors"]


@pytest.mark.asyncio
async def test_executor_command_registered(monkeypatch):
    async def fake_exec(*args, **kwargs):
        class Proc:
            returncode = 0

            async def communicate(self):
                return b"0 passed", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await default_dispatcher.dispatch("executor run")
    assert isinstance(result, dict)
    assert "tests" in result


@pytest.mark.asyncio
async def test_executor_saves_failures_to_memory(monkeypatch, tmp_path):
    async def fake_exec(*args, **kwargs):
        if "pytest" in args:

            class Proc:
                returncode = 1

                async def communicate(self):
                    tb = (
                        "Traceback (most recent call last):\n"
                        '  File "t.py", line 1, in <module>\n'
                        "    foo()\n"
                        "NameError: name 'foo' is not defined\n"
                        "1 failed\n"
                    )
                    return tb.encode(), b""

            return Proc()
        raise FileNotFoundError

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    def fake_lint(self, paths):
        return []

    monkeypatch.setattr(AstLinter, "lint_paths", fake_lint)

    jarvis = type("J", (), {"memory": MemoryManager(str(tmp_path / "mem.json"))})()
    default_dispatcher.jarvis = jarvis

    result = await executor.run(".")
    stored = jarvis.memory.recall("tests.last_failures")
    assert stored == result["errors"]


@pytest.mark.asyncio
async def test_review_failures_command(monkeypatch, tmp_path):
    jarvis = type("J", (), {"memory": MemoryManager(str(tmp_path / "mem.json"))})()
    await jarvis.memory.remember(
        "tests.last_failures",
        [{"traceback": {"error": "Boom"}, "suggestions": ["fix it"]}],
    )
    default_dispatcher.jarvis = jarvis

    output = await default_dispatcher.dispatch("executor review_failures")
    assert "Boom" in output
    assert "fix it" in output
