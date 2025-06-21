import asyncio
import importlib
import sys
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from enum import Enum, auto
from functools import wraps
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationError

from utils.logger import get_logger

logger = get_logger().getChild("ModuleManager")

# ========================
# ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ
# ========================


class ModuleState(Enum):
    UNLOADED = auto()
    LOADING = auto()
    LOADED = auto()
    ERROR = auto()
    RELOADING = auto()


class ModuleEvent(BaseModel):
    name: str
    data: Dict[str, Any]
    timestamp: float = time.time()


class ModuleConfig(BaseModel):
    enabled: bool = True
    priority: int = 50
    dependencies: List[str] = []
    sandboxed: bool = False
    expected_hash: Optional[str] = None
    resource_limits: Dict[str, int] = {"cpu_time": 1, "memory_mb": 256}


class JarvisModule(ABC):
    @abstractmethod
    async def setup(self, jarvis: Any, config: Dict) -> bool: ...

    @abstractmethod
    async def cleanup(self) -> None: ...

    async def health_check(self) -> bool:
        return True

    async def handle_event(self, event: ModuleEvent) -> bool:
        return False

    async def run_tests(self) -> Dict[str, Any]:
        return {"status": "no_tests"}


# ========================
# ДЕКОРАТОРЫ И УТИЛИТЫ
# ========================


def module_error_handler(func):
    @wraps(func)
    async def wrapper(self, module_name: str, *args, **kwargs):
        try:
            return await func(self, module_name, *args, **kwargs)
        except ModuleNotFoundError:
            logger.error(f"Module {module_name} not found")
        except ValidationError as e:
            logger.error(f"Config error in {module_name}: {e}")
        except Exception as e:
            logger.exception(
                f"Unexpected error in {func.__name__} for {module_name}",
                exc_info=e,
            )
        return False

    return wrapper


@contextmanager
def time_operation(operation_name: str):
    start = time.monotonic()
    yield
    logger.debug(f"{operation_name} took {time.monotonic() - start:.2f}s")


def apply_resource_limits(limits: Dict[str, int]):
    """No-op after removing sandbox limits."""
    return


# ========================
# ОСНОВНОЙ КЛАСС
# ========================


class ModuleManager:
    def __init__(self, jarvis: Any):
        self.jarvis = jarvis
        self.modules: Dict[str, Any] = {}
        self.module_states: Dict[str, ModuleState] = {}
        self.module_configs: Dict[str, ModuleConfig] = {}
        self.module_events: Dict[str, List[ModuleEvent]] = {}
        self.lock = asyncio.Lock()
        self.MIN_MODULE_VERSION = "1.0.0"

    # ------------------------
    # ОСНОВНЫЕ МЕТОДЫ
    # ------------------------

    @module_error_handler
    async def load_module(
        self, module_name: str, config: Optional[Dict] = None
    ) -> bool:
        async with self.lock:
            if module_name in self.modules:
                logger.warning(f"Module {module_name} already loaded")
                return True

            self.module_states[module_name] = ModuleState.LOADING
            self.module_events[module_name] = []

            try:
                module_config = ModuleConfig(**(config or {}))
                self.module_configs[module_name] = module_config
            except ValidationError as e:
                logger.error(f"Invalid config for {module_name}: {e}")
                self.module_states[module_name] = ModuleState.ERROR
                return False

            if not await self._verify_module_security(module_name, module_config):
                self.module_states[module_name] = ModuleState.ERROR
                return False

            if not await self._load_dependencies(module_name, module_config):
                self.module_states[module_name] = ModuleState.ERROR
                return False

            with time_operation(f"Module {module_name} load"):
                module = await self._initialize_module(module_name, module_config)
                if not module:
                    return False

            self.modules[module_name] = module
            self.module_states[module_name] = ModuleState.LOADED
            logger.info(f"Module {module_name} loaded successfully")
            return True

    @module_error_handler
    async def unload_module(self, module_name: str) -> bool:
        async with self.lock:
            if module_name not in self.modules:
                logger.warning(f"Module {module_name} not found")
                return False

            self.module_states[module_name] = ModuleState.RELOADING
            module = self.modules.pop(module_name)

            if hasattr(module, "cleanup"):
                with time_operation(f"Module {module_name} cleanup"):
                    await module.cleanup()

            module_path = f"jarvis.modules.{module_name}"
            if module_path in sys.modules:
                del sys.modules[module_path]

            self.module_states[module_name] = ModuleState.UNLOADED
            logger.info(f"Module {module_name} unloaded")
            return True

    async def reload_module(self, module_name: str) -> bool:
        config = self.module_configs.get(module_name, {})
        if not await self.unload_module(module_name):
            return False
        return await self.load_module(module_name, config.dict())

    # ------------------------
    # ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ
    # ------------------------

    async def send_event(self, module_name: str, event_name: str, data: Dict) -> bool:
        """Отправка события модулю."""
        if module_name not in self.modules:
            return False

        event = ModuleEvent(name=event_name, data=data)
        self.module_events[module_name].append(event)

        if hasattr(self.modules[module_name], "handle_event"):
            return await self.modules[module_name].handle_event(event)
        return False

    async def run_module_tests(self, module_name: str) -> Dict[str, Any]:
        """Запуск тестов модуля."""
        if module_name not in self.modules:
            return {"error": "module_not_loaded"}

        if hasattr(self.modules[module_name], "run_tests"):
            return await self.modules[module_name].run_tests()
        return {"status": "no_tests"}

    async def health_check_all(self) -> Dict[str, bool]:
        """Проверка здоровья всех модулей."""
        results = {}
        for name, module in self.modules.items():
            results[name] = await module.health_check()
        return results

    async def shutdown(self, timeout: float = 5.0) -> None:
        """Корректное завершение работы."""
        tasks = [self.unload_module(name) for name in self.modules]
        await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)

    # ------------------------
    # ПРИВАТНЫЕ МЕТОДЫ
    # ------------------------

    async def _verify_module_security(
        self, module_name: str, config: ModuleConfig
    ) -> bool:
        return True

    async def _load_dependencies(self, module_name: str, config: ModuleConfig) -> bool:
        for dep in config.dependencies:
            if dep not in self.modules:
                if not await self.load_module(dep):
                    logger.error(f"Dependency {dep} for {module_name} failed to load")
                    return False
        return True

    async def _initialize_module(
        self, module_name: str, config: ModuleConfig
    ) -> Optional[JarvisModule]:
        try:
            module = importlib.import_module(f"jarvis.modules.{module_name}")
            if not hasattr(module, "setup"):
                logger.error(f"Module {module_name} has no setup function")
                return None

            if not await self._check_module_compatibility(module):
                return None

            return await module.setup(self.jarvis, config.dict())
        except Exception as e:
            logger.error(f"Module {module_name} initialization failed: {str(e)}")
            return None

    async def _check_module_compatibility(self, module: Any) -> bool:
        module_version = getattr(module, "__version__", "0.0.0")
        if module_version < self.MIN_MODULE_VERSION:
            logger.error(
                f"Module version {module_version} is below minimum required {self.MIN_MODULE_VERSION}"
            )
            return False
        return True
