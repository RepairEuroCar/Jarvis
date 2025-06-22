import pytest

from jarvis.core.main import Jarvis, UserEvent


@pytest.mark.asyncio
async def test_rating_stored_in_memory():
    jarvis = Jarvis()
    code = "x = 1\n"
    await jarvis.brain.log_thoughts("simple", {"generated_code": code})
    rec = jarvis.brain.get_chain_of_thought(limit=1)[0]
    assert "rating" in rec
    assert rec["rating"]["brevity"]["lines"] == 1


@pytest.mark.asyncio
async def test_rate_solutions_command():
    jarvis = Jarvis()
    code = "def foo():\n    eval('2+2')\n"
    await jarvis.brain.log_thoughts("risk", {"generated_code": code})
    event = UserEvent(user_id=0, text="rate_solutions")
    result = await jarvis.rate_solutions_command(event)
    assert "risky=" in result
