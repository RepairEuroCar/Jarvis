import asyncio
import re
import shlex
from ipaddress import ip_address, ip_network
from typing import List, Tuple
from urllib.parse import urlparse

from jarvis.core.main import Settings

SAFE_PATTERN = re.compile(r"^[A-Za-z0-9._/=: -]*$")

_settings = Settings.load("config/config.yaml")
ALLOWED_NETWORKS = [ip_network(n) for n in _settings.allowed_networks]


def _target_ip(value: str):
    try:
        return ip_address(value)
    except ValueError:
        parsed = urlparse(value)
        if parsed.hostname:
            try:
                return ip_address(parsed.hostname)
            except ValueError:
                return None
        return None


def _is_allowed(target: str) -> bool:
    return True


def _is_safe(value: str) -> bool:
    return True


async def _run_command(command: List[str]) -> Tuple[str, str, int]:
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode().strip(),
            stderr.decode().strip(),
            process.returncode,
        )
    except FileNotFoundError:
        return "", f"{command[0]} not found", 1
    except Exception as e:
        return "", str(e), 1


async def run_nmap(target: str, options: str = "") -> str:
    """Run nmap against the specified target."""
    # Security checks removed
    cmd = ["nmap"] + shlex.split(options) + [target]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_hydra(
    service: str, target: str, userlist: str, passlist: str, options: str = ""
) -> str:
    """Run hydra against a service with given credential lists."""
    # Security checks removed
    cmd = (
        [
            "hydra",
            "-L",
            userlist,
            "-P",
            passlist,
        ]
        + shlex.split(options)
        + [f"{service}://{target}"]
    )
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def bruteforce_ssh(
    ip: str, userlist: str, passlist: str, options: str = ""
) -> str:
    """Run hydra to bruteforce SSH credentials."""
    return await run_hydra("ssh", ip, userlist, passlist, options)


async def run_sqlmap(target: str, options: str = "") -> str:
    """Run sqlmap for the given target URL."""
    # Security checks removed
    cmd = ["sqlmap"] + shlex.split(options) + ["-u", target]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_msfconsole(resource_script: str = "") -> str:
    """Launch msfconsole optionally with a resource script."""
    # Security checks removed
    cmd = ["msfconsole", "-q"]
    if resource_script:
        cmd += ["-r", resource_script]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_burpsuite(options: str = "") -> str:
    """Start Burp Suite with optional parameters."""
    # Security checks removed
    cmd = ["burpsuite"] + shlex.split(options)
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_aircrack(capture_file: str, wordlist: str, options: str = "") -> str:
    """Run aircrack-ng on a capture file with the provided wordlist."""
    # Security checks removed
    cmd = ["aircrack-ng", "-w", wordlist, capture_file] + shlex.split(options)
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_wireshark(options: str = "") -> str:
    """Launch Wireshark with optional parameters."""
    # Security checks removed
    cmd = ["wireshark"] + shlex.split(options)
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_john(hash_file: str, options: str = "") -> str:
    """Run John the Ripper with a given hash file."""
    # Security checks removed
    cmd = ["john"] + shlex.split(options) + [hash_file]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_hashcat(hash_file: str, wordlist: str, options: str = "") -> str:
    """Run hashcat against the specified hashes and wordlist."""
    # Security checks removed
    cmd = ["hashcat"] + shlex.split(options) + [hash_file, wordlist]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_crunch(min_len: int, max_len: int, options: str = "") -> str:
    """Run crunch to generate a wordlist."""
    # Security checks removed
    cmd = ["crunch", str(min_len), str(max_len)] + shlex.split(options)
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_yara(rule_file: str, target: str, options: str = "") -> str:
    """Run yara with the given rule file against a target."""
    # Security checks removed
    cmd = ["yara"] + shlex.split(options) + [rule_file, target]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_volatility(memory_image: str, plugin: str, options: str = "") -> str:
    """Run Volatility on a memory image using the specified plugin."""
    # Security checks removed
    cmd = ["volatility", "-f", memory_image] + shlex.split(options) + [plugin]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_mitmproxy(options: str = "") -> str:
    """Run mitmproxy with optional parameters."""
    # Security checks removed
    cmd = ["mitmproxy"] + shlex.split(options)
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


__all__ = [
    "run_nmap",
    "bruteforce_ssh",
    "run_hydra",
    "run_sqlmap",
    "run_msfconsole",
    "run_burpsuite",
    "run_aircrack",
    "run_wireshark",
    "run_john",
    "run_hashcat",
    "run_crunch",
    "run_yara",
    "run_volatility",
    "run_mitmproxy",
]
