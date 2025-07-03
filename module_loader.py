import json
import logging
from pathlib import Path
from typing import List, Tuple

from jsonschema import validate, ValidationError

from jarvis.core.module_manager import ModuleManager, ModuleConfig

logger = logging.getLogger(__name__)


MANIFEST_SCHEMA = {
    "type": "object",
    "required": ["module"],
    "properties": {
        "module": {"type": "string"},
        "enabled": {"type": "boolean"},
        "priority": {"type": "integer"},
        "config": {"type": "object"},
    },
}


class ModuleLoader:
    """Load Jarvis modules from ``.manifest`` files."""

    def __init__(self, manager: ModuleManager, modules_dir: str = "modules", state_file: str = "module_state.json") -> None:
        self.manager = manager
        self.modules_dir = Path(modules_dir)
        self.state_file = Path(state_file)
        self.loaded: List[str] = []

    def _find_manifests(self) -> List[Path]:
        return list(self.modules_dir.rglob("*.manifest"))

    def _parse_manifest(self, path: Path) -> Tuple[int, str, dict] | None:
        try:
            data = json.loads(path.read_text())
            validate(data, MANIFEST_SCHEMA)
            if not data.get("enabled", True):
                return None
            return (
                data.get("priority", 50),
                data["module"],
                data.get("config", {}),
            )
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Invalid manifest %s: %s", path, exc)
            return None

    def _load_manifest_list(self) -> List[Tuple[int, str, dict]]:
        manifests = []
        for path in self._find_manifests():
            parsed = self._parse_manifest(path)
            if parsed:
                manifests.append(parsed)
        return sorted(manifests, key=lambda x: x[0])

    async def load_all(self) -> bool:
        """Load all modules defined by manifests."""
        manifests = self._load_manifest_list()
        for _priority, name, cfg in manifests:
            success = await self.manager.load_module(name, cfg)
            if not success:
                logger.error("Failed to load %s, rolling back", name)
                for loaded in list(reversed(self.loaded)):
                    await self.manager.unload_module(loaded)
                self.loaded.clear()
                return False
            self.loaded.append(name)
        self._save_state()
        return True

    def _save_state(self) -> None:
        try:
            self.state_file.write_text(json.dumps({"loaded": self.loaded}))
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.warning("Failed to save module state: %s", exc)

    def restore_state(self) -> List[str]:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self.loaded = data.get("loaded", [])
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.warning("Failed to load module state: %s", exc)
        return self.loaded
