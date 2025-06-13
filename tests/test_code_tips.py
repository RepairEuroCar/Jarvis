import pytest

from jarvis.core.main import Jarvis, UserEvent


@pytest.mark.asyncio
async def test_code_tips_command(tmp_path):
    code = "x = 1\n"
    p = tmp_path / "sample.py"
    p.write_text(code, encoding="utf-8")
    jarvis = Jarvis()
    event = UserEvent(user_id=0, text=f"code_tips {p}")
    result = await jarvis.code_tips_command(event)
    assert "Global variable" in result
