"""Utilities for performing basic AST-based lint checks."""

import ast
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml


@dataclass
class LintError:
    """Container describing a single lint violation."""

    filepath: str
    lineno: int
    message: str


class AstLinter:
    """Simple AST-based linter that can load settings from a policy file."""

    def __init__(
        self,
        max_function_lines: int | None = None,
        policy_path: str | os.PathLike[str] = "train/coding_policy.yaml",
    ) -> None:
        """Initialize the linter.

        Parameters
        ----------
        max_function_lines:
            Maximum allowed length of a function body. If ``None``, the value
            will be loaded from ``policy_path`` or default to ``50``.
        policy_path:
            Path to the coding policy YAML file.
        """

        self._config = self._load_policy(Path(policy_path))
        self.max_function_lines = (
            max_function_lines
            if max_function_lines is not None
            else self._config.get("linting", {}).get("max_function_lines", 50)
        )
        lint_cfg = self._config.get("linting", {})
        self.disallow_globals = lint_cfg.get("disallow_globals", True)
        self.disallow_top_level_calls = lint_cfg.get("disallow_top_level_calls", True)
        self.check_eval_exec = lint_cfg.get("check_eval_exec", True)

    @staticmethod
    def _load_policy(path: Path) -> dict:
        if not path.is_file():
            return {}
        try:
            with open(path, encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
        except Exception:
            return {}

    def _lint_source(self, source: str, path: str) -> list[LintError]:
        """Run lint checks on given source code."""
        errors: list[LintError] = []
        tree = ast.parse(source, filename=path)

        for node in tree.body:
            if self.disallow_globals and isinstance(
                node, (ast.Assign, ast.AugAssign, ast.AnnAssign)
            ):
                errors.append(
                    LintError(
                        path,
                        node.lineno,
                        "Global variable assignment not allowed",
                    )
                )
            if (
                self.disallow_top_level_calls
                and isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
            ):
                errors.append(
                    LintError(
                        path,
                        node.lineno,
                        "Top-level call detected during import",
                    )
                )

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = node.end_lineno or node.lineno
                length = end - node.lineno + 1
                if length > self.max_function_lines:
                    msg = (
                        f"Function '{node.name}' too long "
                        f"({length} > {self.max_function_lines})"
                    )
                    errors.append(
                        LintError(
                            path,
                            node.lineno,
                            msg,
                        )
                    )
            if isinstance(node, ast.Call) and self.check_eval_exec:
                func = node.func
                if isinstance(func, ast.Name) and func.id in {"eval", "exec"}:
                    errors.append(
                        LintError(
                            path,
                            node.lineno,
                            f"Potential code injection via '{func.id}'",
                        )
                    )
                if (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.attr in {"eval", "exec"}
                ):
                    errors.append(
                        LintError(
                            path,
                            node.lineno,
                            f"Potential code injection via '{func.attr}'",
                        )
                    )
        return errors

    def lint_file(self, path: str) -> list[LintError]:
        """Run lint checks on a single Python file.

        Args:
            path (str): Path to the file to lint.

        Returns:
            list[LintError]: list of found lint errors.
        """
        with open(path, encoding="utf-8") as f:
            source = f.read()
        return self._lint_source(source, path)

    def lint_text(self, source: str, path: str = "<string>") -> list[LintError]:
        """Lint Python code provided as a string."""
        return self._lint_source(source, path)

    def lint_paths(self, paths: Iterable[str]) -> list[LintError]:
        """Lint multiple files or directories.

        Args:
            paths (Iterable[str]):
                Collection of file or directory paths to check.

        Returns:
            list[LintError]: Combined lint errors for all provided paths.
        """
        all_errors: list[LintError] = []
        for p in paths:
            if os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for fname in files:
                        if fname.endswith(".py"):
                            file_path = os.path.join(root, fname)
                            all_errors.extend(self.lint_file(file_path))
            else:
                all_errors.extend(self.lint_file(p))
        return all_errors


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run simple AST lint checks")
    parser.add_argument(
        "paths",
        nargs="+",
        help="Files or directories to lint",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        help="Maximum allowed function body length (overrides policy)",
    )
    parser.add_argument(
        "--policy",
        type=str,
        default="train/coding_policy.yaml",
        help="Path to coding policy YAML file",
    )
    args = parser.parse_args()

    linter = AstLinter(
        max_function_lines=args.max_lines,
        policy_path=args.policy,
    )
    errors = linter.lint_paths(args.paths)
    for err in errors:
        print(f"{err.filepath}:{err.lineno}: {err.message}")
    raise SystemExit(1 if errors else 0)
