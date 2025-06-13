import pytest

from jarvis.core.main import Jarvis, UserEvent
from jarvis.goal_manager import GoalManager
from modules import kali_tools


def test_set_and_get_goal():
    jarvis = Jarvis()
    jarvis.goals.set_goal("check vulnerabilities", "security")
    data = jarvis.goals.get_goal()
    assert data["goal"] == "check vulnerabilities"
    assert data["motivation"] == "security"


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
