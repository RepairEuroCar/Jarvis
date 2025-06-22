import pytest

from jarvis.memory.manager import MemoryManager
from jarvis.memory.project_experience import (
    ProjectExperience,
    load_experiences,
    query_experiences,
    save_experience,
)


@pytest.mark.asyncio
async def test_save_and_load(tmp_path):
    mem = MemoryManager(str(tmp_path / "mem.json"))
    exp = ProjectExperience(
        task="Fix bug",
        code_refs=["fix.py"],
        outcome="success",
        tags=["bug"],
    )
    await save_experience(mem, exp)
    loaded = load_experiences(mem)
    assert len(loaded) == 1
    assert loaded[0].task == "Fix bug"


@pytest.mark.asyncio
async def test_query(tmp_path):
    mem = MemoryManager(str(tmp_path / "mem.json"))
    await save_experience(
        mem,
        ProjectExperience(
            task="Add feature",
            code_refs=["f.py"],
            outcome="done",
            tags=["feature"],
        ),
    )
    await save_experience(
        mem,
        ProjectExperience(
            task="Fix bug",
            code_refs=["b.py"],
            outcome="done",
            tags=["bug"],
        ),
    )
    by_tag = query_experiences(mem, tags=["bug"])
    assert len(by_tag) == 1 and by_tag[0].task == "Fix bug"
    by_text = query_experiences(mem, text="Add feature")
    assert len(by_text) == 1 and by_text[0].task == "Add feature"
