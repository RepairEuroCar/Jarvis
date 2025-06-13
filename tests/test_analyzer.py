import asyncio
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
