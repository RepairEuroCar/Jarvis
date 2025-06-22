import ast
import os
from typing import Iterable, List

from utils.docstring_helper import _indent_lines

PLACEHOLDER = "Auto-generated summary."


def _is_placeholder(doc: str | None) -> bool:
    if not doc:
        return False
    return doc.strip().startswith(PLACEHOLDER)


def _summary_for_module(tree: ast.Module, path: str) -> str:
    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    parts = []
    if classes:
        parts.append(f"classes: {', '.join(classes)}")
    if funcs:
        parts.append(f"functions: {', '.join(funcs)}")
    if not parts:
        name = os.path.basename(path).replace('.py', '')
        return f"{name} module."
    return "Contains " + "; ".join(parts) + "."


def _summary_for_class(node: ast.ClassDef) -> str:
    methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if methods:
        return f"Class {node.name} with methods: {', '.join(methods)}."
    return f"Class {node.name}."


def _summary_for_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = [a.arg for a in node.args.args if a.arg not in {'self', 'cls'}]
    if args:
        return f"Function {node.name} with parameters {', '.join(args)}."
    return f"Function {node.name}."


def _docstring_lines(text: str, indent: str) -> List[str]:
    return _indent_lines(f'"""{text}"""', indent)


def enhance_file(path: str) -> bool:
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source, filename=path)
    lines = source.splitlines()
    updated = False

    module_doc = ast.get_docstring(tree, clean=False)
    first = tree.body[0] if tree.body else None
    if module_doc is None or _is_placeholder(module_doc):
        summary = _summary_for_module(tree, path)
        doc_lines = [f'"""{summary}"""']
        if module_doc is None:
            insert_idx = 1 if lines and lines[0].startswith('#!') else 0
            lines[insert_idx:insert_idx] = doc_lines
        elif isinstance(first, ast.Expr) and isinstance(getattr(first, 'value', None), ast.Str):
            start = first.lineno - 1
            end = first.end_lineno or start + 1
            lines[start:end] = doc_lines
        updated = True

    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            body_first = node.body[0] if node.body else None
            if doc is None or _is_placeholder(doc):
                if isinstance(node, ast.ClassDef):
                    summary = _summary_for_class(node)
                else:
                    summary = _summary_for_function(node)
                indent = ' ' * (node.col_offset + 4)
                new_lines = _docstring_lines(summary, indent)
                if doc is None:
                    insert_at = body_first.lineno - 1 if body_first else node.lineno
                    lines[insert_at:insert_at] = new_lines
                elif isinstance(body_first, ast.Expr) and isinstance(getattr(body_first, 'value', None), ast.Str):
                    start = body_first.lineno - 1
                    end = body_first.end_lineno or start + 1
                    lines[start:end] = new_lines
                updated = True

    if updated:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    return updated


def enhance_paths(paths: Iterable[str]) -> List[str]:
    changed: List[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for fname in files:
                    if fname.endswith('.py'):
                        fpath = os.path.join(root, fname)
                        if enhance_file(fpath):
                            changed.append(fpath)
        else:
            if p.endswith('.py') and os.path.isfile(p):
                if enhance_file(p):
                    changed.append(p)
    return changed


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Enhance docstrings in project.')
    parser.add_argument('paths', nargs='+', help='Files or directories to process')
    args = parser.parse_args()

    modified = enhance_paths(args.paths)
    for m in modified:
        print(f'Updated {m}')
