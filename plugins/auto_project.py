from __future__ import annotations

import os
import py_compile
from typing import List

from jarvis.commands.registry import CommandCategory, CommandInfo
from jarvis.core.main import RegisteredCommand
from modules.task_splitter import analyze_spec
from utils.code_generator import write_code


def _generate_and_compile(spec_text: str, out_dir: str) -> List[str]:
    """Generate Python modules from *spec_text* and compile them."""
    tasks = analyze_spec(spec_text)
    os.makedirs(out_dir, exist_ok=True)
    results: List[str] = []
    for idx, task in enumerate(tasks, 1):
        path = os.path.join(out_dir, f"task_{idx}.py")
        write_code({"dsl": task, "path": path, "description": task})
        try:
            py_compile.compile(path, doraise=True)
            results.append(path)
        except py_compile.PyCompileError as exc:  # pragma: no cover - syntax error
            results.append(f"{path} [compile error: {exc.msg}]")
    return results


def register(jarvis) -> None:
    async def auto_project(event):
        parts = event.text.split(maxsplit=2)
        if len(parts) < 3:
            return "Usage: auto_project <spec_file> <output_dir>"
        spec_file, out_dir = parts[1], parts[2]
        if not os.path.isfile(spec_file):
            return f"Spec file not found: {spec_file}"
        with open(spec_file, encoding="utf-8") as f:
            text = f.read()
        paths = _generate_and_compile(text, out_dir)
        return "Generated:\n" + "\n".join(paths)

    jarvis.commands["auto_project"] = RegisteredCommand(
        info=CommandInfo(
            name="auto_project",
            description="Generate modules from spec and compile them",
            category=CommandCategory.DEVELOPMENT,
            usage="auto_project <spec_file> <output_dir>",
            aliases=["auto_proj"],
        ),
        handler=auto_project,
    )
