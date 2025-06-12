# -----------------------------
# tests/test_brain.py,
# -----------------------------
import pytest
import asyncio
from jarvis.core.main import Jarvis

@pytest.mark.asyncio
async def test_brain_logical():
    jarvis = Jarvis()
    context = {"user_name": "Tester"}
    result = await jarvis.brain.think("Если пойдет дождь, то мы отменим прогулку", context)
    assert result["status"].startswith("completed")
    assert result["processed_by"] == "LogicalThoughtProcessor"
    assert "дождь" in result["conclusion"]

@pytest.mark.asyncio
async def test_brain_creative():
    jarvis = Jarvis()
    context = {"num_creative_ideas": 2}
    result = await jarvis.brain.think("Придумай идею для мобильного приложения", context)
    assert result["status"].startswith("creative")
    assert len(result["ideas"]) == 2

@pytest.mark.asyncio
async def test_brain_analytical():
    jarvis = Jarvis()
    context = {}
    result = await jarvis.brain.think("Проанализируй данные: 10, 20, 30, 40", context)
    assert result["status"].startswith("completed")
    assert result["analysis"]["metrics"]["sum"] == 100
