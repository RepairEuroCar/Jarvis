import pytest

from command_dispatcher import CommandDispatcher
from modules import task_splitter


def test_analyze_spec_bullets():
    text = "- create file\n* add tests"
    tasks = task_splitter.analyze_spec(text)
    assert tasks == ["create file", "add tests"]


def test_analyze_spec_verbs():
    text = "Implement login. Fix bug."
    tasks = task_splitter.analyze_spec(text)
    assert tasks == ["Implement login", "Fix bug"]


@pytest.mark.asyncio
async def test_task_split_command(tmp_path):
    spec = tmp_path / "spec.txt"
    spec.write_text("- a\n- b", encoding="utf-8")
    dispatcher = CommandDispatcher()
    task_splitter.register_commands(dispatcher)
    result = await dispatcher.dispatch(f"task_split --file={spec}")
    assert "1. a" in result
    assert "2. b" in result
