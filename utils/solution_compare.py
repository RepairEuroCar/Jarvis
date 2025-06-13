import ast
import difflib


def structural_diff(code_a: str, code_b: str) -> str:
    """Return a unified diff of AST dumps for two code snippets."""
    tree_a = ast.parse(code_a)
    tree_b = ast.parse(code_b)
    dump_a = ast.dump(tree_a, include_attributes=False, indent=2)
    dump_b = ast.dump(tree_b, include_attributes=False, indent=2)
    diff = difflib.unified_diff(
        dump_a.splitlines(),
        dump_b.splitlines(),
        fromfile="previous",
        tofile="current",
        lineterm="",
    )
    return "\n".join(diff)


__all__ = ["structural_diff"]
