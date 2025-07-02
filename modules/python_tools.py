"""Python development tools."""

import logging
import sys
from pathlib import Path

from command_dispatcher import CommandDispatcher, default_dispatcher
from core.metrics.module_usage import track_usage
from modules import executor

logger = logging.getLogger(__name__)

TEMPLATES = {
    "cli": (
        "#!/usr/bin/env python\n"
        "import argparse\n\n\n"
        "def main():\n"
        "    parser = argparse.ArgumentParser(description='CLI script')\n"
        "    parser.add_argument('--name', default='World')\n"
        "    args = parser.parse_args()\n"
        "    print(f'Hello, {args.name}!')\n\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    ),
    "web": (
        "from flask import Flask\n\n"
        "app = Flask(__name__)\n\n\n"
        "@app.route('/')\n"
        "def index():\n"
        "    return 'Hello, world!'\n\n\n"
        "if __name__ == '__main__':\n"
        "    app.run()\n"
    ),
    "utility": (
        "def main():\n"
        "    print('Utility script')\n\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    ),
}


@track_usage("python_tools")
async def create_script(name: str, skeleton_type: str = "cli") -> str:
    """Create a python script with given skeleton."""
    template = TEMPLATES.get(skeleton_type)
    if not template:
        raise ValueError(f"Unknown skeleton_type: {skeleton_type}")
        
    path = Path(f"{name}.py")
    path.write_text(template)
    return str(path)


@track_usage("python_tools")
async def run_tests(target: str = ".") -> dict:
    """Run pytest on target directory."""
    return await executor.run(target)


@track_usage("python_tools")
async def lint(target: str = ".") -> dict:
    """Run linter on target directory."""
    result = await executor.run(target)
    return {"warnings": result.get("lint", {}).get("warnings", [])}


def register_commands(
    dispatcher: CommandDispatcher = default_dispatcher
) -> None:
    """Register python commands."""
    dispatcher.register_command_handler(
        "python", 
        "create_script", 
        create_script
    )
    dispatcher.register_command_handler(
        "python", 
        "run_tests", 
        run_tests
    )
    dispatcher.register_command_handler(
        "python", 
        "lint", 
        lint
    )


register_commands(default_dispatcher)


async def health_check() -> bool:
    """Check Python interpreter is accessible."""
    try:
        return Path(sys.executable).exists()
    except Exception as exc:
        logger.warning("Python tools health check failed: %s", exc)
        return False


__all__ = [
    "create_script",
    "run_tests", 
    "lint",
    "register_commands",
]