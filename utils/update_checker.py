import asyncio
import subprocess
from pathlib import Path

from utils.logger import get_logger

logger = get_logger().getChild("UpdateChecker")


async def _git(*args: str, repo_path: str = ".") -> tuple[int, str]:
    """Run a git command and return (returncode, stdout)."""
    proc = await asyncio.create_subprocess_exec(
        "git", *args, "--no-pager", cwd=repo_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        logger.error("git %s failed: %s", ' '.join(args), err.decode().strip())
    return proc.returncode, out.decode().strip()


async def check_for_updates(repo_path: str, remote: str = "origin", branch: str = "main") -> str | None:
    """Return latest commit hash from remote if newer than local, else None."""
    rc, local = await _git("rev-parse", branch, repo_path=repo_path)
    if rc != 0:
        return None
    rc, remote_head = await _git("ls-remote", remote, branch, repo_path=repo_path)
    if rc != 0 or not remote_head:
        return None
    remote_hash = remote_head.split()[0]
    if local.strip() != remote_hash:
        return remote_hash
    return None
