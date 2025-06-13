import asyncio
import shlex
from typing import List, Tuple

INVALID_PATTERNS = [";", "&&", "|", "`", "$(", ")", ">"]


def _is_safe(value: str) -> bool:
    return not any(p in value for p in INVALID_PATTERNS)


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
    if not _is_safe(target) or not _is_safe(options):
        return "Invalid target or options"
    cmd = ["nmap"] + shlex.split(options) + [target]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def bruteforce_ssh(
    ip: str, userlist: str, passlist: str, options: str = ""
) -> str:
    """Run hydra to bruteforce SSH credentials."""
    if not all(_is_safe(x) for x in [ip, userlist, passlist, options]):
        return "Invalid arguments"
    cmd = (
        ["hydra", "-L", userlist, "-P", passlist]
        + shlex.split(options)
        + [f"ssh://{ip}"]
    )
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_sqlmap(target: str, options: str = "") -> str:
    """Run sqlmap for the given target URL."""
    if not _is_safe(target) or not _is_safe(options):
        return "Invalid target or options"
    cmd = ["sqlmap"] + shlex.split(options) + ["-u", target]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_msfconsole(resource_script: str = "") -> str:
    """Launch msfconsole optionally with a resource script."""
    if resource_script and not _is_safe(resource_script):
        return "Invalid resource script"
    cmd = ["msfconsole", "-q"]
    if resource_script:
        cmd += ["-r", resource_script]
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


async def run_burpsuite(options: str = "") -> str:
    """Start Burp Suite with optional parameters."""
    if not _is_safe(options):
        return "Invalid options"
    cmd = ["burpsuite"] + shlex.split(options)
    stdout, stderr, rc = await _run_command(cmd)
    return stdout if rc == 0 else f"Error: {stderr}"


__all__ = [
    "run_nmap",
    "bruteforce_ssh",
    "run_sqlmap",
    "run_msfconsole",
    "run_burpsuite",
]
