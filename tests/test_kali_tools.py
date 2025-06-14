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
async def test_run_hydra(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"hydr", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("0.0.0.0/0")])
    result = await kali_tools.run_hydra(
        "ftp",
        "1.2.3.4",
        "users.txt",
        "pass.txt",
    )
    assert "hydra" in called["args"][0]
    assert "ftp://1.2.3.4" in called["args"]
    assert "hydr" in result


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
async def test_run_john(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"john", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await kali_tools.run_john("hashes.txt")
    assert called["args"][0] == "john"
    assert "john" in result


@pytest.mark.asyncio
async def test_run_hashcat(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"hash", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await kali_tools.run_hashcat("hashes.txt", "wordlist.txt")
    assert called["args"][0] == "hashcat"
    assert "hash" in result


@pytest.mark.asyncio
async def test_run_crunch(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"cr", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await kali_tools.run_crunch(1, 3)
    assert called["args"][0] == "crunch"
    assert "cr" in result


@pytest.mark.asyncio
async def test_run_yara(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"yr", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await kali_tools.run_yara("rule.yar", "target.bin")
    assert called["args"][0] == "yara"
    assert "yr" in result


@pytest.mark.asyncio
async def test_run_volatility(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"vol", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await kali_tools.run_volatility("mem.img", "pslist")
    assert called["args"][0] == "volatility"
    assert "vol" in result


@pytest.mark.asyncio
async def test_run_mitmproxy(monkeypatch):
    called = {}

    async def fake_exec(*args, **kwargs):
        called["args"] = args

        class Proc:
            returncode = 0

            async def communicate(self):
                return b"mitm", b""

        return Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await kali_tools.run_mitmproxy("--version")
    assert called["args"][0] == "mitmproxy"
    assert "mitm" in result


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
    called = False

    async def fake_run(cmd):
        nonlocal called
        called = True
        return "", "", 0

    monkeypatch.setattr(kali_tools, "_run_command", fake_run)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("10.0.0.0/8")])
    result = await kali_tools.run_nmap("8.8.8.8")
    assert not called
    assert "not allowed" in result.lower()


@pytest.mark.asyncio
async def test_invalid_inputs_blocked(monkeypatch):
    called = []

    async def fake_run(cmd):
        called.append(cmd)
        return "", "", 0

    monkeypatch.setattr(kali_tools, "_run_command", fake_run)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("0.0.0.0/0")])

    await kali_tools.run_nmap("127.0.0.1; rm -rf /")
    await kali_tools.bruteforce_ssh("1.2.3.4", "users.txt", "pass.txt", "--opt;")
    await kali_tools.run_hydra("ssh", "1.2.3.4", "u.txt", "p.txt", "--bad;")
    await kali_tools.run_sqlmap("http://test/;", "")
    await kali_tools.run_msfconsole("bad.sh;")
    await kali_tools.run_burpsuite(";--bad")
    await kali_tools.run_aircrack("cap.cap", "dict.txt", "--bssid;")
    await kali_tools.run_john("hashes;")
    await kali_tools.run_hashcat("hashes;", "dict;", "--mode;")
    await kali_tools.run_crunch(1, 2, "-t ;")
    await kali_tools.run_yara("rule;", "target;", "--opt;")
    await kali_tools.run_volatility("mem;", "pslist;", "--opt;")
    await kali_tools.run_mitmproxy("--o;")
    await kali_tools.run_wireshark("--random;")

    assert len(called) == 0


@pytest.mark.asyncio
async def test_unsafe_inputs_blocked(monkeypatch):
    called = []

    async def fake_run(cmd):
        called.append(cmd)
        return "", "", 0

    monkeypatch.setattr(kali_tools, "_run_command", fake_run)
    monkeypatch.setattr(kali_tools, "ALLOWED_NETWORKS", [ip_network("0.0.0.0/0")])

    await kali_tools.run_nmap("127.0.0.1", "-A && rm")
    await kali_tools.bruteforce_ssh("1.2.3.4", "users.txt", "pass.txt", "-f &&")
    await kali_tools.run_hydra("ssh", "1.2.3.4", "u", "p", "-x &&")
    await kali_tools.run_sqlmap("http://test", "--risk 3 &&")
    await kali_tools.run_msfconsole("bad.rc &&")
    await kali_tools.run_burpsuite("--tmp && id")
    await kali_tools.run_aircrack("cap.cap", "dict.txt", "--bssid &&")
    await kali_tools.run_john("hash &&")
    await kali_tools.run_hashcat("h", "d", "--mode &&")
    await kali_tools.run_crunch(1, 3, "-t &&")
    await kali_tools.run_yara("rule", "target", "--x &&")
    await kali_tools.run_volatility("mem", "pslist", "--plug &&")
    await kali_tools.run_mitmproxy("--cmd &&")
    await kali_tools.run_wireshark("--cmd &&")

    assert len(called) == 0
