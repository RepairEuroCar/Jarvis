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
async def test_run_aircrack(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"air", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await kali_tools.run_aircrack("capture.cap", "words.txt")
    assert called["args"][0] == "aircrack-ng"
    assert "air" in result


@pytest.mark.asyncio
async def test_run_wireshark(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"wire", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await kali_tools.run_wireshark("--help")
    assert called["args"][0] == "wireshark"
    assert "wire" in result


@pytest.mark.asyncio
async def test_disallowed_target(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"scan", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("10.0.0.0/8")])
    result = await kali_tools.run_nmap("8.8.8.8")
    assert called["args"][0] == "nmap"
    assert "scan" in result


@pytest.mark.asyncio
async def test_invalid_inputs_allowed(monkeypatch):
    called = []

    async def fake_run(cmd):
        called.append(cmd)
        return "", "", 0

    monkeypatch.setattr(kali_tools, "_run_command", fake_run)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("0.0.0.0/0")])

    await kali_tools.run_nmap("127.0.0.1; rm -rf /")
    await kali_tools.bruteforce_ssh("1.2.3.4", "users.txt", "pass.txt", "--opt;")
    await kali_tools.run_sqlmap("http://test/;", "")
    await kali_tools.run_msfconsole("bad.sh;")
    await kali_tools.run_burpsuite(";--bad")
    await kali_tools.run_aircrack("cap.cap", "dict.txt", "--bssid;")
    await kali_tools.run_wireshark("--random;")

    assert len(called) == 7


@pytest.mark.asyncio
async def test_unsafe_inputs_allowed(monkeypatch):
    called = []

    async def fake_run(cmd):
        called.append(cmd)
        return "", "", 0

    monkeypatch.setattr(kali_tools, "_run_command", fake_run)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("0.0.0.0/0")])

    await kali_tools.run_nmap("127.0.0.1", "-A && rm")
    await kali_tools.bruteforce_ssh("1.2.3.4", "users.txt", "pass.txt", "-f &&")
    await kali_tools.run_sqlmap("http://test", "--risk 3 &&")
    await kali_tools.run_msfconsole("bad.rc &&")
    await kali_tools.run_burpsuite("--tmp && id")
    await kali_tools.run_aircrack("cap.cap", "dict.txt", "--bssid &&")
    await kali_tools.run_wireshark("--cmd &&")

    assert len(called) == 7
