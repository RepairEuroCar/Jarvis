import asyncio
import json
import pytest

from jarvis.core.main import Jarvis
from modules.analyzer import AdvancedCodeAnalyzer


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_detect_magic_numbers_and_duplicates(tmp_path):
    code = (
        "CONST = 10\n"
        "x = 5\n"
        "\n"
        "def foo():\n"
        "    y = 1\n"
        "    z = 5\n"
        "    return y + z\n"
        "\n"
        "def bar():\n"
        "    y = 1\n"
        "    z = 5\n"
        "    return y + z\n"
    )
    p = tmp_path / "sample.py"
    p.write_text(code, encoding="utf-8")

    analyzer = AdvancedCodeAnalyzer(Jarvis())
    report, err = run(analyzer.generate_comprehensive_report(str(p)))
    assert err is None
    file_rep = report["files"][0]

    magic_vals = [m["value"] for m in file_rep.get("magic_numbers", [])]
    assert 5 in magic_vals and 1 in magic_vals

    globals_names = [g["name"] for g in file_rep.get("globals", [])]
    assert "x" in globals_names

    assert file_rep.get("duplicate_code")


@pytest.mark.asyncio
async def test_pylint_integration(monkeypatch, tmp_path):
    p = tmp_path / "a.py"
    p.write_text("print('hi')\n", encoding="utf-8")

    async def fake_exec(*args, **kwargs):
        class Proc:
            returncode = 0

            async def communicate(self):
                out = json.dumps([
                    {
                        "type": "warning",
                        "line": 1,
                        "message": "dummy",
                        "symbol": "dummy",
                        "message-id": "W0001",
                    }
                ]).encode()
                return out, b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    analyzer = AdvancedCodeAnalyzer(Jarvis())
    report, err = await analyzer.generate_comprehensive_report(str(p))
    assert err is None
    warns = report["files"][0].get("pylint_warnings")
    assert warns and warns[0]["message_id"] == "W0001"
