"""Utility to generate large Python files for testing or demonstration."""

from __future__ import annotations

import ast
import os
from typing import Dict

from utils.import_inference import infer_imports
from utils.python_dsl import phrase_to_python


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


CATEGORY_TEMPLATES: dict[str, str] = {
    "utility": "{code}\n",
    "web": (
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n\n"
        "{code}\n\n"
        "if __name__ == '__main__':\n"
        "    app.run()\n"
    ),
    "cli": (
        "import argparse\n\n"
        "def main():\n"
        "    parser = argparse.ArgumentParser()\n"
        "    # add arguments here\n"
        "    args = parser.parse_args()\n"
        "    pass\n\n"
        "{code}\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    ),
}


def dsl_to_python(dsl_text: str) -> str:
    """Convert simple DSL instructions to Python code using AST metaprogramming."""
    module = ast.Module(body=[], type_ignores=[])
    for line in dsl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        snippet = phrase_to_python(line)
        try:
            snippet_ast = ast.parse(snippet)
        except SyntaxError:
            continue
        module.body.extend(snippet_ast.body)

    try:
        return ast.unparse(module)
    except AttributeError:  # pragma: no cover - Python <3.9 fallback
        try:
            import astor
        except Exception as exc:  # pragma: no cover - extremely unlikely
            raise RuntimeError("Unable to unparse AST") from exc
        return astor.to_source(module)


def generate_template(category: str, code: str) -> str:
    """Wrap generated code into a template based on the task category."""
    template = CATEGORY_TEMPLATES.get(category, CATEGORY_TEMPLATES["utility"])
    return template.replace("{code}", code)


def write_code(task: dict[str, str]) -> str:
    """Generate Python code from a task description and write it to file.

    Parameters
    ----------
    task: dict[str, str]
        Dictionary with keys ``dsl`` containing DSL text, ``category`` defining
        template category, ``path`` with output file path and optional
        ``description`` used for inferring imports.

    Returns
    -------
    str
        Absolute path of the generated file.
    """
    dsl_text = task.get("dsl", "")
    category = task.get("category", "utility")
    path = task.get("path", "generated.py")
    description = task.get("description", "")

    python_code = dsl_to_python(dsl_text)
    final_code = generate_template(category, python_code)

    if description:
        imports = infer_imports(description)
        if imports:
            final_code = "\n".join(imports) + "\n\n" + final_code

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(final_code)

    return os.path.abspath(path)


__all__ = [
    "generate_large_python_file",
    "dsl_to_python",
    "generate_template",
    "write_code",
]
