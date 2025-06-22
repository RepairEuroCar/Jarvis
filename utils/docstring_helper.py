"""Utilities for inserting placeholder docstrings."""

import ast
import os
from pathlib import Path
from typing import Iterable, List

import yaml


def _generate_docstring(node: ast.AST | None, style: str, kind: str) -> str:
    """Return a placeholder docstring for the given ``kind``."""
    if style == "sphinx":
        if kind == "function" and isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            lines = ['"""', "Auto-generated summary.", ""]
            for arg in [a.arg for a in node.args.args if a.arg not in {"self", "cls"}]:
                lines.append(f":param {arg}: TODO")
            if node.returns:
                lines.append(":return: TODO")
            lines.append('"""')
            return "\n".join(lines)
        return '"""Auto-generated summary."""'

    # default google style
    if kind == "function" and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = [a.arg for a in node.args.args if a.arg not in {"self", "cls"}]
        lines = ['"""', "Auto-generated summary."]
        if args or node.returns:
            lines.append("")
        if args:
            lines.append("Args:")
            for arg in args:
                lines.append(f"    {arg} (Any): TODO")
        if node.returns:
            lines.append("")
            lines.append("Returns:")
            lines.append("    Any: TODO")
        lines.append('"""')
        return "\n".join(lines)
    return '"""Auto-generated summary."""'


def _indent_lines(text: str, indent: str) -> List[str]:
    """Indent each line of ``text`` by ``indent``."""
    return [f"{indent}{line}" if line else indent for line in text.splitlines()]


def _load_style(policy_path: str | os.PathLike[str]) -> str:
    path = Path(policy_path)
    if not path.is_file():
        return "google"
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
            return cfg.get("docstring", {}).get("style", "google")
    except Exception:
        return "google"


def process_file(
    path: str,
    style: str | None = None,
    policy_path: str | os.PathLike[str] = "train/coding_policy.yaml",
) -> bool:
    """Insert placeholder docstrings into ``path`` if they are missing."""
    if style is None:
        style = _load_style(policy_path)
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename=path)
    lines = source.splitlines()
    insertions: List[tuple[int, List[str]]] = []

    if ast.get_docstring(tree) is None:
        doc = _generate_docstring(None, style, "module")
        insert_idx = 1 if lines and lines[0].startswith("#!") else 0
        insertions.append((insert_idx, doc.splitlines()))

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and ast.get_docstring(node) is None:
            doc = _generate_docstring(node, style, "class")
            indent = " " * (node.col_offset + 4)
            insertions.append(
                (
                    node.body[0].lineno - 1 if node.body else node.lineno,
                    _indent_lines(doc, indent),
                )
            )
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and ast.get_docstring(node) is None
        ):
            doc = _generate_docstring(node, style, "function")
            indent = " " * (node.col_offset + 4)
            insertions.append(
                (
                    node.body[0].lineno - 1 if node.body else node.lineno,
                    _indent_lines(doc, indent),
                )
            )

    if not insertions:
        return False
    insertions.sort(reverse=True, key=lambda t: t[0])
    for idx, new_lines in insertions:
        lines[idx:idx] = new_lines

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return True


def process_paths(
    paths: Iterable[str],
    style: str | None = None,
    policy_path: str | os.PathLike[str] = "train/coding_policy.yaml",
) -> List[str]:
    """Process multiple file or directory paths."""
    changed: List[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for fname in files:
                    if fname.endswith(".py"):
                        fpath = os.path.join(root, fname)
                        if process_file(fpath, style, policy_path):
                            changed.append(fpath)
        else:
            if process_file(p, style, policy_path):
                changed.append(p)
    return changed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Insert template docstrings.")
    parser.add_argument("paths", nargs="+", help="Files or directories to process")
    parser.add_argument("--style", choices=["google", "sphinx"], help="Docstring style")
    parser.add_argument(
        "--policy",
        type=str,
        default="train/coding_policy.yaml",
        help="Path to coding policy YAML file",
    )
    args = parser.parse_args()

    modified = process_paths(args.paths, style=args.style, policy_path=args.policy)
    for m in modified:
        print(f"Updated {m}")
