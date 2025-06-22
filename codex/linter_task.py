from utils.linter import AstLinter


def run_basic_linter(path: str, max_lines: int = 50) -> list[str]:
    """Lint *path* using :class:`AstLinter` and return messages."""
    linter = AstLinter(max_function_lines=max_lines)
    errors = linter.lint_paths([path])
    return [f"{e.filepath}:{e.lineno}: {e.message}" for e in errors]
