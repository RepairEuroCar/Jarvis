import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_module_map = {
    # Base dependencies
    "memory": "jarvis.memory",
    "memory.manager": "jarvis.memory.manager",
    "memory.core": "jarvis.memory.core",
    "memory.knowledge_base": "jarvis.memory.knowledge_base",
    "memory.project_experience": "jarvis.memory.project_experience",
    "voice": "voice",
    "voice.interface": "voice.interface",
    "commands": "commands",
    "commands.registry": "commands.registry",
    # NLU is used inside core
    "nlu": "jarvis.nlp",
    # Core itself
    "core": "jarvis.core",
    # Expose Jarvis class directly
    "core.main": "jarvis.core.main",
    "goal_manager": "jarvis.goal_manager",
    "reasoning_engine": "jarvis.reasoning_engine",
}

for alias, target in _module_map.items():
    try:
        sys.modules[f"{__name__}.{alias}"] = importlib.import_module(target)
    except Exception:
        pass

# Expose modules as the ``jarvis.modules`` subpackage
for path in (ROOT / "modules").glob("*.py"):
    mod_name = path.stem
    if mod_name == "__init__":
        continue
    try:
        sys.modules[f"jarvis.modules.{mod_name}"] = importlib.import_module(
            f"modules.{mod_name}"
        )
    except Exception:
        # Skip modules that fail to import due to optional dependencies
        pass
