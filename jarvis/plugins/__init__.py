import importlib.util
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import ModuleType

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


def _load_directory(jarvis, directory: Path) -> None:
    """Load all plugins from a specific directory."""
    if not directory.exists():
        logger.info("Plugin directory %s does not exist", directory)
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


def load_plugins(
    jarvis, plugin_dir: str, extra_dirs: Sequence[str] | None = None
) -> None:
    """Discover and load plugins from *plugin_dir* and *extra_dirs*."""
    _load_directory(jarvis, Path(plugin_dir))
    for d in extra_dirs or []:
        _load_directory(jarvis, Path(d).expanduser())
