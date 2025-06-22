import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable

from utils.logger import get_logger

logger = get_logger().getChild("plugins")


def _iter_module_files(directory: Path) -> Iterable[Path]:
    """Yield Python module files from *directory*."""
    if not directory.exists():
        return
    for item in directory.iterdir():
        if item.is_file() and item.suffix == ".py":
            yield item
        elif item.is_dir() and (item / "__init__.py").is_file():
            yield item / "__init__.py"


def _load_module(path: Path) -> ModuleType | None:
    name = (
        f"plugins.{path.stem}"
        if path.name != "__init__.py"
        else f"plugins.{path.parent.name}"
    )
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        logger.warning("Cannot create spec for %s", path)
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        logger.warning("Failed loading plugin %s: %s", path, exc)
        return None
    return module


def load_plugins(jarvis, plugin_dir: str) -> None:
    """Discover and load plugins from *plugin_dir*."""
    directory = Path(plugin_dir)
    if not directory.exists():
        logger.info("Plugin directory %s does not exist", plugin_dir)
        return

    for mod_path in _iter_module_files(directory):
        module = _load_module(mod_path)
        if not module:
            continue
        register = getattr(module, "register", None)
        if callable(register):
            try:
                register(jarvis)
                logger.debug("Registered plugin %s", mod_path)
            except Exception as exc:
                logger.warning("Plugin %s raised during register: %s", mod_path, exc)
        else:
            logger.debug("Plugin %s has no register() function", mod_path)
