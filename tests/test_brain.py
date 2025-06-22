# -----------------------------
# tests/test_brain.py,
# -----------------------------

import pytest

from jarvis.core.main import Jarvis


@pytest.mark.asyncio
async def test_brain_logical():
    jarvis = Jarvis()
    context = {"user_name": "Tester"}
    result = await jarvis.brain.think(
        "Если пойдет дождь, то мы отменим прогулку", context
    )
    assert result["status"].startswith("completed")
    assert result["processed_by"] == "LogicalThoughtProcessor"
    assert "дождь" in result["conclusion"]


@pytest.mark.asyncio
async def test_brain_creative():
    jarvis = Jarvis()
    context = {"num_creative_ideas": 2}
    result = await jarvis.brain.think(
        "Придумай идею для мобильного приложения", context
    )
    assert result["status"].startswith("creative")
    assert len(result["ideas"]) == 2


@pytest.mark.asyncio
async def test_brain_analytical():
    jarvis = Jarvis()
    context = {}
    result = await jarvis.brain.think("Проанализируй данные: 10, 20, 30, 40", context)
    assert result["status"].startswith("completed")
    assert result["analysis"]["metrics"]["sum"] == 100


@pytest.mark.asyncio
async def test_log_thoughts_direct():
    jarvis = Jarvis()
    await jarvis.brain.log_thoughts("dummy task", {"ok": True})
    chain = jarvis.brain.get_chain_of_thought(limit=1)
    assert chain
    assert chain[-1]["problem"] == "dummy task"
    assert chain[-1]["solution"]["ok"] is True


@pytest.mark.asyncio
async def test_chain_of_thought_after_think():
    jarvis = Jarvis()
    await jarvis.brain.think("Если завтра снег, то останемся дома", {})
    chain = jarvis.brain.get_chain_of_thought()
    assert any("снег" in rec["problem"] for rec in chain)


@pytest.mark.asyncio
async def test_brain_self_evolve(tmp_path):
    sample = "def FooBar():\n    MyVar=1\n    return MyVar\n"
    f = tmp_path / "sample.py"
    f.write_text(sample, encoding="utf-8")
    jarvis = Jarvis()
    result = await jarvis.brain.self_evolve(directory=tmp_path)
    assert str(f) in result
    assert "my_var" in result[str(f)]["diff"]


@pytest.mark.asyncio
async def test_brain_self_review():
    jarvis = Jarvis()
    code = "x = 1\nprint('hi')\n"
    await jarvis.brain.log_thoughts("test", {"generated_code": code})
    review = jarvis.brain.self_review()
    assert review
    warnings = list(review.values())[0]["warnings"]
    assert any("Global variable" in w for w in warnings)


@pytest.mark.asyncio
async def test_summarize_recent_thoughts():
    jarvis = Jarvis()
    await jarvis.brain.log_thoughts("task one", {"status": "done"})
    await jarvis.brain.log_thoughts("task two", {"status": "failed"})
    summary = jarvis.brain.summarize_recent_thoughts(limit=2)
    assert "task one" in summary and "done" in summary
    assert "task two" in summary and "failed" in summary


@pytest.mark.asyncio
async def test_find_similar_solution():
    jarvis = Jarvis()
    await jarvis.brain.log_thoughts(
        "как приготовить борщ",
        {"answer": "Используй свёклу", "status": "completed"},
    )
    result = jarvis.brain.find_similar_solution("как приготовить борщ быстро")
    assert result is not None
    assert result["answer"] == "Используй свёклу"


@pytest.mark.asyncio
async def test_compare_recent_code_and_self_review_diff():
    jarvis = Jarvis()
    first = "x = 1\n"
    second = "x = 2\n"
    await jarvis.brain.log_thoughts("repeat", {"generated_code": first})
    await jarvis.brain.log_thoughts("repeat", {"generated_code": second})

    diffs = jarvis.brain.compare_recent_code(limit=2)
    assert "repeat" in diffs
    assert "value=Constant(value=1)" in diffs["repeat"]

    review = jarvis.brain.self_review()
    assert "repeat" in review
    assert "structural_diff" in review["repeat"]
