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
}

for alias, target in _module_map.items():
    try:
        sys.modules[f"{__name__}.{alias}"] = importlib.import_module(target)
    except Exception:
        pass
