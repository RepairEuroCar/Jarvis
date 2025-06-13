"""TODO: add summary."""

import ast
import os
from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class LintError:
    """TODO: add summary."""

    filepath: str
    lineno: int
    message: str


class AstLinter:
    """Simple AST-based linter."""

    def __init__(self, max_function_lines: int = 50):
        """
        TODO: add summary.

        Args:
            max_function_lines (Any): TODO
        """
        self.max_function_lines = max_function_lines

    def lint_file(self, path: str) -> List[LintError]:
        """
        TODO: add summary.

        Args:
            path (Any): TODO

        Returns:
            Any: TODO
        """
        errors: List[LintError] = []
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=path)

        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                errors.append(
                    LintError(
                        path, node.lineno, "Global variable assignment not allowed"
                    )
                )
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                errors.append(
                    LintError(
                        path, node.lineno, "Top-level call detected during import"
                    )
                )

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = node.end_lineno or node.lineno
                length = end - node.lineno + 1
                if length > self.max_function_lines:
                    errors.append(
                        LintError(
                            path,
                            node.lineno,
                            f"Function '{node.name}' too long ({length} > {self.max_function_lines})",
                        )
                    )
        return errors

    def lint_paths(self, paths: Iterable[str]) -> List[LintError]:
        """
        TODO: add summary.

        Args:
            paths (Any): TODO

        Returns:
            Any: TODO
        """
        all_errors: List[LintError] = []
        for p in paths:
            if os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for fname in files:
                        if fname.endswith(".py"):
                            all_errors.extend(self.lint_file(os.path.join(root, fname)))
            else:
                all_errors.extend(self.lint_file(p))
        return all_errors


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run simple AST lint checks")
    parser.add_argument("paths", nargs="+", help="Files or directories to lint")
    parser.add_argument(
        "--max-lines",
        type=int,
        default=50,
        help="Maximum allowed function body length",
    )
    args = parser.parse_args()

    linter = AstLinter(max_function_lines=args.max_lines)
    errors = linter.lint_paths(args.paths)
    for err in errors:
        print(f"{err.filepath}:{err.lineno}: {err.message}")
    raise SystemExit(1 if errors else 0)
