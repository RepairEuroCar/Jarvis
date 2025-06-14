import asyncio
from ipaddress import ip_network

import pytest

from modules import kali_tools


@pytest.mark.asyncio
async def test_run_nmap(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"ok", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("0.0.0.0/0")])
    result = await kali_tools.run_nmap("127.0.0.1")
    assert called["args"][0] == "nmap"
    assert "ok" in result


@pytest.mark.asyncio
async def test_bruteforce_ssh(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"done", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("0.0.0.0/0")])
    result = await kali_tools.bruteforce_ssh("1.2.3.4", "users.txt", "pass.txt")
    assert "hydra" in called["args"][0]
    assert "done" in result


@pytest.mark.asyncio
async def test_disallowed_target(monkeypatch):
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("10.0.0.0/8")])
    result = await kali_tools.run_nmap("8.8.8.8")
    assert "not in allowed networks" in result


@pytest.mark.asyncio
async def test_invalid_inputs_rejected(monkeypatch):
    async def fake_run(*args, **kwargs):
        raise AssertionError("command should not run")

    monkeypatch.setattr(kali_tools, "_run_command", fake_run)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("0.0.0.0/0")])

    assert "Invalid target or options" in await kali_tools.run_nmap(
        "127.0.0.1; rm -rf /"
    )
    assert "Invalid target or options" in await kali_tools.bruteforce_ssh(
        "1.2.3.4", "users.txt", "pass.txt", "--opt;"
    )
    assert "Invalid target or options" in await kali_tools.run_sqlmap(
        "http://test/;", ""
    )
    assert "Invalid target or options" in await kali_tools.run_msfconsole("bad.sh;")
    assert "Invalid target or options" in await kali_tools.run_burpsuite(";--bad")


@pytest.mark.asyncio
async def test_unsafe_and_inputs(monkeypatch):
    async def fake_run(*args, **kwargs):
        raise AssertionError("command should not run")

    monkeypatch.setattr(kali_tools, "_run_command", fake_run)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("0.0.0.0/0")])

    assert "Invalid target or options" in await kali_tools.run_nmap(
        "127.0.0.1", "-A && rm"
    )
    assert "Invalid target or options" in await kali_tools.bruteforce_ssh(
        "1.2.3.4", "users.txt", "pass.txt", "-f &&"
    )
    assert "Invalid target or options" in await kali_tools.run_sqlmap(
        "http://test", "--risk 3 &&"
    )
    assert "Invalid target or options" in await kali_tools.run_msfconsole("bad.rc &&")
    assert "Invalid target or options" in await kali_tools.run_burpsuite("--tmp && id")
