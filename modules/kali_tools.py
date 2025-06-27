import asyncio
import re
import shlex
from ipaddress import ip_address, ip_network
from typing import List, Tuple
from urllib.parse import urlparse

from jarvis.core.main import Settings
import logging

logger = logging.getLogger(__name__)

SAFE_PATTERN = re.compile(r"^[A-Za-z0-9._/=: -]*$")

_settings = Settings.load("config/config.yaml")
ALLOWED_NETWORKS = [ip_network(n) for n in _settings.allowed_networks]


def reload_allowed_networks(
    settings: Settings | None = None, config_path: str = "config/config.yaml"
) -> None:
    """Reload ``ALLOWED_NETWORKS`` from Jarvis settings.

    If ``settings`` is not provided, the configuration is loaded from
    ``config_path`` using :class:`jarvis.core.main.Settings`.
    """
    global _settings, ALLOWED_NETWORKS
    _settings = settings or Settings.load(config_path)
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
    ip = _target_ip(target)
    if ip is None:
        return False
    return any(ip in net for net in ALLOWED_NETWORKS)


def _is_safe(value: str) -> bool:
    return bool(SAFE_PATTERN.fullmatch(value))


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


async def health_check() -> bool:
    """Verify that core penetration tools are installed."""
    import shutil

    try:
        return shutil.which("nmap") is not None
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("Kali tools health check failed: %s", exc)
        return False


async def run_nmap(target: str, options: str = "") -> str:
    """Run nmap against the specified target."""
    if not _is_allowed(target) or not _is_safe(options):
        return "Target not allowed or unsafe options."
    cmd = ["nmap"] + shlex.split(options) + [target]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_hydra(
    service: str, target: str, userlist: str, passlist: str, options: str = ""
) -> str:
    """Run hydra against a service with given credential lists."""
    if not _is_allowed(target) or not all(
        _is_safe(v) for v in [service, userlist, passlist, options]
    ):
        return "Invalid arguments."
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
    if not _is_allowed(target) or not _is_safe(target) or not _is_safe(options):
        return "Invalid target or options."
    cmd = ["sqlmap"] + shlex.split(options) + ["-u", target]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_msfconsole(resource_script: str = "") -> str:
    """Launch msfconsole optionally with a resource script."""
    if resource_script and not _is_safe(resource_script):
        return "Unsafe resource script."
    cmd = ["msfconsole", "-q"]
    if resource_script:
        cmd += ["-r", resource_script]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_burpsuite(options: str = "") -> str:
    """Start Burp Suite with optional parameters."""
    if not _is_safe(options):
        return "Unsafe options."
    cmd = ["burpsuite"] + shlex.split(options)
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_aircrack(capture_file: str, wordlist: str, options: str = "") -> str:
    """Run aircrack-ng on a capture file with the provided wordlist."""
    if not all(_is_safe(v) for v in [capture_file, wordlist, options]):
        return "Unsafe arguments."
    cmd = ["aircrack-ng", "-w", wordlist, capture_file] + shlex.split(options)
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_wireshark(options: str = "") -> str:
    """Launch Wireshark with optional parameters."""
    if not _is_safe(options):
        return "Unsafe options."
    cmd = ["wireshark"] + shlex.split(options)
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_john(hash_file: str, options: str = "") -> str:
    """Run John the Ripper with a given hash file."""
    if not all(_is_safe(v) for v in [hash_file, options]):
        return "Unsafe arguments."
    cmd = ["john"] + shlex.split(options) + [hash_file]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_hashcat(hash_file: str, wordlist: str, options: str = "") -> str:
    """Run hashcat against the specified hashes and wordlist."""
    if not all(_is_safe(v) for v in [hash_file, wordlist, options]):
        return "Unsafe arguments."
    cmd = ["hashcat"] + shlex.split(options) + [hash_file, wordlist]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_crunch(min_len: int, max_len: int, options: str = "") -> str:
    """Run crunch to generate a wordlist."""
    if not _is_safe(options):
        return "Unsafe options."
    cmd = ["crunch", str(min_len), str(max_len)] + shlex.split(options)
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_yara(rule_file: str, target: str, options: str = "") -> str:
    """Run yara with the given rule file against a target."""
    if not all(_is_safe(v) for v in [rule_file, target, options]):
        return "Unsafe arguments."
    cmd = ["yara"] + shlex.split(options) + [rule_file, target]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_volatility(memory_image: str, plugin: str, options: str = "") -> str:
    """Run Volatility on a memory image using the specified plugin."""
    if not all(_is_safe(v) for v in [memory_image, plugin, options]):
        return "Unsafe arguments."
    cmd = ["volatility", "-f", memory_image] + shlex.split(options) + [plugin]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_mitmproxy(options: str = "") -> str:
    """Run mitmproxy with optional parameters."""
    if not _is_safe(options):
        return "Unsafe options."
    cmd = ["mitmproxy"] + shlex.split(options)
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


__all__ = [
    "reload_allowed_networks",
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
