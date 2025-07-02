import ast
import asyncio
import os
from typing import list

from jarvis.processors.test_generator import TestGeneratorProcessor


async def _generate_for_function(source: str, name: str) -> str:
    proc = TestGeneratorProcessor()
    result = await proc.process(
        "generate", {"function_name": name, "source_code": source}
    )
    return result.get("generated_test", "")


def generate_autotests(source_path: str, out_dir: str) -> list[str]:
    """Generate basic pytest tests for each function in *source_path*."""
    with open(source_path, encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source)
    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            test_code = asyncio.run(_generate_for_function(source, node.name))
            if test_code:
                fname = os.path.join(out_dir, f"test_{node.name}.py")
                with open(fname, "w", encoding="utf-8") as out:
                    out.write(test_code)
                written.append(fname)
    return written
