import asyncio
import sys
from pathlib import Path

from command_dispatcher import CommandDispatcher, default_dispatcher
from modules import executor
from core.metrics.module_usage import track_usage
import logging

logger = logging.getLogger(__name__)

TEMPLATES = {
    "cli": """#!/usr/bin/env python\nimport argparse\n\n\n def main():\n    parser = argparse.ArgumentParser(description='CLI script')\n    parser.add_argument('--name', default='World')\n    args = parser.parse_args()\n    print(f'Hello, {args.name}!')\n\n\n if __name__ == '__main__':\n    main()\n""",
    "web": """from flask import Flask\n\napp = Flask(__name__)\n\n\n@app.route('/')\ndef index():\n    return 'Hello, world!'\n\n\n if __name__ == '__main__':\n    app.run()\n""",
    "utility": """def main():\n    print('Utility script')\n\n\n if __name__ == '__main__':\n    main()\n""",
}


@track_usage("python_tools")
async def create_script(name: str, skeleton_type: str = "cli") -> str:
    """Create a python script with given *name* and *skeleton_type*."""
    template = TEMPLATES.get(skeleton_type)
    if not template:
        raise ValueError(f"Unknown skeleton_type: {skeleton_type}")
    path = Path(f"{name}.py")
    path.write_text(template)
    return str(path)


@track_usage("python_tools")
async def run_tests(target: str = ".") -> dict:
    """Run pytest and lint on *target* directory."""
    return await executor.run(target)


@track_usage("python_tools")
async def lint(target: str = ".") -> dict:
    """Run lint on *target* directory."""
    result = await executor.run(target)
    return {"warnings": result.get("lint", {}).get("warnings", [])}


def register_commands(dispatcher: CommandDispatcher = default_dispatcher) -> None:
    dispatcher.register_command_handler("python", "create_script", create_script)
    dispatcher.register_command_handler("python", "run_tests", run_tests)
    dispatcher.register_command_handler("python", "lint", lint)


register_commands(default_dispatcher)


async def health_check() -> bool:
    """Check that Python interpreter is accessible."""
    try:
        return Path(sys.executable).exists()
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("Python tools health check failed: %s", exc)
        return False

__all__ = [
    "create_script",
    "run_tests",
    "lint",
    "register_commands",
]
