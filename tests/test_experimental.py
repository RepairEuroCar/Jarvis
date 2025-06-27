import logging
import pytest

from utils.experimental import experimental_feature, experimental_usage


def test_experimental_decorator_warns_and_counts(caplog):
    @experimental_feature("low")
    def foo(x):
        return x * 2

    with caplog.at_level(logging.WARNING):
        result = foo(3)

    assert result == 6
    assert any("Experimental feature foo activated" in r.message for r in caplog.records)
    assert experimental_usage["foo"] == 1


@pytest.mark.asyncio
async def test_run_nmap_logs_experimental(monkeypatch, caplog):
    from modules import kali_tools
    async def fake_run(cmd):
        return "", "", 0

    monkeypatch.setattr(kali_tools, "_run_command", fake_run)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [kali_tools.ip_network("0.0.0.0/0")])

    before = experimental_usage.get("run_nmap", 0)
    with caplog.at_level(logging.WARNING):
        await kali_tools.run_nmap("127.0.0.1")

    assert any("Experimental feature run_nmap activated" in r.message for r in caplog.records)
    assert experimental_usage["run_nmap"] == before + 1
