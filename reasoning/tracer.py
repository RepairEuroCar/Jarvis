"""Utilities for parsing Python traceback strings."""

from __future__ import annotations

import re
from typing import List, Dict, Any


_FRAME_RE = re.compile(r"\s*File \"(?P<file>[^\"]+)\", line (?P<line>\d+)(?:, in (?P<func>.+))?")
_ERROR_RE = re.compile(r"^(?P<error>[\w.]+Error:.*)$")


def parse_tracebacks(text: str) -> List[Dict[str, Any]]:
    """Extract traceback information from ``text``.

    Parameters
    ----------
    text:
        Raw output potentially containing one or more Python tracebacks.

    Returns
    -------
    list of dict
        Each dict contains ``frames`` and ``error`` keys describing a traceback.
    """
    results: List[Dict[str, Any]] = []
    segments = text.split("Traceback (most recent call last):")
    for seg in segments[1:]:
        frames: List[Dict[str, Any]] = []
        lines = seg.strip().splitlines()
        for line in lines:
            m = _FRAME_RE.match(line)
            if m:
                frames.append(
                    {
                        "file": m.group("file"),
                        "line": int(m.group("line")),
                        "func": (m.group("func") or "").strip(),
                    }
                )
        error = ""
        for line in reversed(lines):
            m = _ERROR_RE.match(line.strip())
            if m:
                error = m.group("error")
                break
        results.append({"frames": frames, "error": error})
    return results


def suggest_fixes(error_message: str) -> List[str]:
    """Return simple heuristic fixes for ``error_message``."""
    suggestions: List[str] = []
    m = re.search(r"NameError: name '([^']+)' is not defined", error_message)
    if m:
        name = m.group(1)
        suggestions.append(f"Check if '{name}' is defined or imported")
    m = re.search(r"ModuleNotFoundError: No module named '([^']+)'", error_message)
    if m:
        mod = m.group(1)
        suggestions.append(f"Install or add import for module '{mod}'")
    m = re.search(r"ImportError: cannot import name '([^']+)'", error_message)
    if m:
        name = m.group(1)
        suggestions.append(f"Verify import for '{name}' is correct")
    return suggestions


__all__ = ["parse_tracebacks", "suggest_fixes"]
