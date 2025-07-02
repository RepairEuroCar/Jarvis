import re
import subprocess
import sys
from pathlib import Path
from typing import list

from codex.autotest_generation import generate_autotests

FUNC_RE = re.compile(r"^\+\s*(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def run(cmd: list[str]) -> str:
    """Return stdout of a subprocess command."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.stdout


def changed_files(diff_range: str) -> list[str]:
    """Return modified files under core directories for *diff_range*."""
    output = run(["git", "diff", "--name-only", diff_range])
    return [
        f
        for f in output.splitlines()
        if f.startswith("core/") or f.startswith("jarvis/core")
    ]


def parse_added_functions(diff_text: str) -> list[str]:
    """Return function names added in *diff_text*."""
    return [
        m.group(1)
        for m in (FUNC_RE.match(line) for line in diff_text.splitlines())
        if m
    ]


def added_functions(path: str, diff_range: str) -> list[str]:
    diff = run(["git", "diff", diff_range, "--", path])
    return parse_added_functions(diff)


def main(diff_range: str = "HEAD~1") -> list[str]:
    """Generate tests for new functions in modified core files."""
    out_dir = Path("tests/generated")
    written: list[str] = []
    for file in changed_files(diff_range):
        if added_functions(file, diff_range):
            written.extend(generate_autotests(file, str(out_dir)))
    return written


if __name__ == "__main__":
    rng = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    for path in main(rng):
        print(path)
