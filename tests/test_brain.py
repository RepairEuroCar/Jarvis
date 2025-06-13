# -----------------------------
# tests/test_brain.py,
# -----------------------------
import asyncio

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


def test_log_thoughts_direct():
    jarvis = Jarvis()
    jarvis.brain.log_thoughts("dummy task", {"ok": True})
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


def test_brain_self_review():
    jarvis = Jarvis()
    code = "x = 1\nprint('hi')\n"
    jarvis.brain.log_thoughts("test", {"generated_code": code})
    review = jarvis.brain.self_review()
    assert review
    warnings = list(review.values())[0]["warnings"]
    assert any("Global variable" in w for w in warnings)
