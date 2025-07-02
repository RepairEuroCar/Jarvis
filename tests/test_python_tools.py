from pathlib import Path

import pytest

from command_dispatcher import default_dispatcher
from modules import python_tools


@pytest.mark.asyncio
async def test_create_script(tmp_path: Path):
    target = tmp_path / "myscript"
    path = await python_tools.create_script(str(target), "cli")
    created = Path(path)
    assert created.exists()
    assert created.read_text().startswith("#!/usr/bin/env python")


@pytest.mark.asyncio
async def test_run_tests_wrapper(monkeypatch):
    async def fake_run(arg):
        return {"tests": {"passed": 1, "failed": 0}, "lint": {"warnings": []}}

    monkeypatch.setattr(python_tools.executor, "run", fake_run)
    result = await python_tools.run_tests(".")
    assert result["tests"]["passed"] == 1


@pytest.mark.asyncio
async def test_lint_wrapper(monkeypatch):
    async def fake_run(arg):
        return {"lint": {"warnings": ["w"]}}

    monkeypatch.setattr(python_tools.executor, "run", fake_run)
    result = await python_tools.lint(".")
    assert result["warnings"] == ["w"]


@pytest.mark.asyncio
async def test_command_registered(monkeypatch):
    async def fake_run(arg):
        return {"tests": {"passed": 0, "failed": 0}, "lint": {"warnings": []}}

    monkeypatch.setattr(python_tools.executor, "run", fake_run)
    result = await default_dispatcher.dispatch("python run_tests --target=.")
    assert isinstance(result, dict)
    assert "tests" in result
