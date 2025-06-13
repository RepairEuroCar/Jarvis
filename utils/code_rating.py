import ast
from typing import Any, Dict, List

from radon.metrics import mi_visit

from utils.linter import AstLinter


def rate_code(source: str) -> Dict[str, Any]:
    """Return simple quality metrics for provided Python code.

    Parameters
    ----------
    source: str
        Python source code to analyse.

    Returns
    -------
    Dict[str, Any]
        Dictionary with ``brevity``, ``readability`` and ``safety`` keys.
    """
    if not source:
        return {
            "brevity": {"lines": 0, "functions": 0},
            "readability": 0.0,
            "safety": 0,
        }

    lines = len(source.splitlines())
    try:
        tree = ast.parse(source)
        functions = sum(
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            for n in ast.walk(tree)
        )
    except SyntaxError:
        functions = 0
    try:
        mi_score = mi_visit(source, True)
        readability = round(float(mi_score), 2) if mi_score else 0.0
    except Exception:
        readability = 0.0

    linter = AstLinter()
    warnings = linter.lint_text(source)
    risky = [
        w.message
        for w in warnings
        if "code injection" in w.message or "Global variable" in w.message
    ]
    safety = len(risky)

    return {
        "brevity": {"lines": lines, "functions": functions},
        "readability": readability,
        "safety": safety,
    }
