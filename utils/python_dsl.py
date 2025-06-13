"""TODO: add summary."""

import ast
import re
from typing import Any, Dict, List


def parse_technical_description(text: str) -> Dict[str, List[str]]:
    """Extract simple bullet requirements from technical docs."""
    requirements = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("-", "*", "•")) or line[0].isdigit():
            # remove leading numbering or bullets
            line = re.sub(r"^[-*•\d\.\)\s]+", "", line)
            requirements.append(line)
    return {"requirements": requirements}


def phrase_to_python(phrase: str) -> str:
    """Translate a short Russian phrase describing code into Python snippet."""
    pl = phrase.lower().strip()
    m = re.match(r"создай функцию ([a-zA-Z_][a-zA-Z0-9_]*)", pl)
    if m:
        name = m.group(1)
        return f"def {name}():\n    pass\n"
    m = re.match(r"создай класс ([a-zA-Z_][a-zA-Z0-9_]*)", pl)
    if m:
        cls = m.group(1).capitalize()
        return f"class {cls}:\n    pass\n"
    m = re.match(r"импортируй ([a-zA-Z0-9_\.]+)(?: как ([a-zA-Z_][a-zA-Z0-9_]*))?", pl)
    if m:
        mod, alias = m.group(1), m.group(2)
        if alias:
            return f"import {mod} as {alias}\n"
        return f"import {mod}\n"
    return "# Не удалось интерпретировать фразу"


def _spec_to_ast(spec: Any) -> ast.stmt:
    """Recursively convert a simple schema spec to an AST node."""
    if isinstance(spec, str):
        return ast.parse(spec).body[0]

    if not isinstance(spec, dict):
        raise TypeError("Spec must be dict or str")

    spec_type = spec.get("type")
    if spec_type == "Function":
        name = spec.get("name", "func")
        args = [ast.arg(arg=a, annotation=None) for a in spec.get("args", [])]
        body = [_spec_to_ast(b) for b in spec.get("body", [])]
        if not body:
            body = [ast.Pass()]
        func = ast.FunctionDef(
            name=name,
            args=ast.arguments(
                posonlyargs=[],
                args=args,
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=body,
            decorator_list=[],
        )
        return func

    if spec_type == "Loop":
        var = spec.get("var", "i")
        iter_expr = ast.parse(spec.get("iter", "[]")).body[0].value
        body = [_spec_to_ast(b) for b in spec.get("body", [])]
        if not body:
            body = [ast.Pass()]
        return ast.For(
            target=ast.Name(id=var, ctx=ast.Store()),
            iter=iter_expr,
            body=body,
            orelse=[],
        )

    if spec_type == "Class":
        name = spec.get("name", "MyClass")
        body = [_spec_to_ast(b) for b in spec.get("body", [])]
        if not body:
            body = [ast.Pass()]
        return ast.ClassDef(
            name=name,
            bases=[],
            keywords=[],
            body=body,
            decorator_list=[],
        )

    raise ValueError(f"Unknown spec type: {spec_type}")


def build_ast_from_schema(schema: Dict[str, Any]) -> ast.Module:
    """Build a Python ``ast.Module`` from a simple schema description."""
    if schema.get("type") == "Module":
        body_specs = schema.get("body", [])
        nodes = [_spec_to_ast(s) for s in body_specs]
    else:
        nodes = [_spec_to_ast(schema)]
    module = ast.Module(body=nodes, type_ignores=[])
    return ast.fix_missing_locations(module)


def generate_code_from_schema(schema: Dict[str, Any]) -> str:
    """Generate Python code from a schema describing constructs."""
    module_ast = build_ast_from_schema(schema)
    try:
        return ast.unparse(module_ast)
    except AttributeError:  # pragma: no cover - Python <3.9 fallback
        try:
            import astor
        except Exception as exc:  # pragma: no cover - extremely unlikely
            raise RuntimeError("Unable to unparse AST") from exc
        return astor.to_source(module_ast)


__all__ = [
    "parse_technical_description",
    "phrase_to_python",
    "build_ast_from_schema",
    "generate_code_from_schema",
]
