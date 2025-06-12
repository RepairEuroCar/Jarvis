"""Utility to generate large Python files for testing or demonstration."""
from __future__ import annotations

import os


def generate_large_python_file(path: str, num_lines: int = 1000) -> str:
    """Generate a Python file containing a simple function with many lines.

    Parameters
    ----------
    path: str
        Destination file path.
    num_lines: int, default 1000
        How many numbered lines should be generated inside the function body.

    Returns
    -------
    str
        The absolute path to the generated file.
    """
    if num_lines < 0:
        raise ValueError("num_lines must be non-negative")

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    lines: list[str] = [
        "def generated_function():\n",
        "    data = []\n",
    ]
    for i in range(num_lines):
        lines.append(f"    data.append({i})\n")
    lines.append("    return data\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return os.path.abspath(path)
