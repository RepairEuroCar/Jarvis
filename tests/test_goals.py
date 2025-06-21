import pytest

from jarvis.core.main import Jarvis, UserEvent
from modules import kali_tools


def test_add_and_list_goals():
    jarvis = Jarvis()
    jarvis.goals.add_goal("low", priority=1, source="user")
    jarvis.goals.add_goal("high", priority=5, deadline=123.0, source="system")
    goals = jarvis.goals.list_goals()
    assert len(goals) == 2
    assert goals[0]["goal"] == "high"
    assert goals[0]["priority"] == 5
    assert goals[0]["deadline"] == 123.0
    assert goals[1]["goal"] == "low"


def test_remove_goal():
    jarvis = Jarvis()
    jarvis.goals.add_goal("one", priority=1)
    jarvis.goals.add_goal("two", priority=2)
    assert jarvis.goals.remove_goal(0) is True
    goals = jarvis.goals.list_goals()
    assert len(goals) == 1
    assert goals[0]["goal"] == "one"


@pytest.mark.asyncio
async def test_execute_goal_vulnerability(monkeypatch):
    jarvis = Jarvis()
    jarvis.goals.set_goal("проверить уязвимости")

    async def fake_nmap(target: str, options: str = ""):
        return "scan ok"

    monkeypatch.setattr(kali_tools, "run_nmap", fake_nmap)
    event = UserEvent(user_id=0, text="execute_goal")
    result = await jarvis.execute_goal_command(event)
    assert "scan ok" in result
