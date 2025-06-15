import os
from typing import List

from jarvis.commands.registry import CommandCategory, CommandInfo
from jarvis.core.main import RegisteredCommand
from utils.code_generator import write_code
from utils.python_dsl import parse_technical_description


def _generate_files(spec_text: str, out_dir: str) -> List[str]:
    """Create Python files from bullet requirements."""
    parsed = parse_technical_description(spec_text)
    requirements = parsed.get("requirements", [])
    os.makedirs(out_dir, exist_ok=True)
    paths: List[str] = []
    for idx, req in enumerate(requirements, 1):
        fname = f"module_{idx}.py"
        path = os.path.join(out_dir, fname)
        write_code({"dsl": req, "path": path, "description": req})
        paths.append(path)
    return paths


def register(jarvis) -> None:
    async def generate_project(event):
        parts = event.text.split(maxsplit=2)
        if len(parts) < 3:
            return "Usage: generate_project <spec_file> <output_dir>"
        spec_file, out_dir = parts[1], parts[2]
        if not os.path.isfile(spec_file):
            return f"Spec file not found: {spec_file}"
        with open(spec_file, "r", encoding="utf-8") as f:
            text = f.read()
        files = _generate_files(text, out_dir)
        return "Created:\n" + "\n".join(files)

    jarvis.commands["generate_project"] = RegisteredCommand(
        info=CommandInfo(
            name="generate_project",
            description="Generate code from a text spec",
            category=CommandCategory.DEVELOPMENT,
            usage="generate_project <spec_file> <output_dir>",
            aliases=["gen_project"],
        ),
        handler=generate_project,
    )
