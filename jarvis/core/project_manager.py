# -----------------------------
# jarvis/core/project_manager.py
# -----------------------------
import difflib
import inspect
import json
import os
import platform
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union


try:
    import aioredis
except ImportError:  # pragma: no cover - optional dependency
    aioredis = None  # type: ignore

try:
    import docker
except ImportError:  # pragma: no cover - optional dependency
    docker = None  # type: ignore
import patch
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from utils.logger import get_logger

logger = get_logger().getChild("ProjectManager")


class ProjectLifecycleException(Exception):
    """Исключения жизненного цикла проекта"""

    pass


class ProjectTemplateType(Enum):
    BASIC_PYTHON = auto()
    DATA_SCIENCE = auto()
    WEB_APP = auto()
    ML_EXPERIMENT = auto()


@dataclass
class ProjectIntelligence:
    """AI-аналитика проекта"""

    code_patterns: Dict[str, int] = field(default_factory=dict)
    tech_debt_score: float = 0.0
    auto_tags: Set[str] = field(default_factory=set)


@dataclass
class ProjectMetadata:
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"
    tags: Set[str] = field(default_factory=set)
    dependencies: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)


class _TemplateEditHandler(FileSystemEventHandler):
    """Watchdog handler to record file modifications."""

    def __init__(self, manager: "ProjectManager", root: str) -> None:
        super().__init__()
        self.manager = manager
        self.root = root

    def _record(self, src_path: str) -> None:
        rel = os.path.relpath(src_path, self.root)
        self.manager._modified_files.add(rel)

    def on_modified(self, event):
        if not event.is_directory:
            self._record(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._record(event.src_path)


class ProjectManager:
    def __init__(self, jarvis: Any):
        self.jarvis = jarvis
        self.current_project: Optional[Dict[str, Any]] = None
        self._project_history: List[Dict[str, Any]] = []
        self._MAX_HISTORY = 10
        self._CONFIG_FILE = ".jarvis_project"
        self._hooks: Dict[str, List[Callable]] = {
            "pre_create": [],
            "post_create": [],
            "pre_close": [],
            "post_close": [],
        }
        self._redis = None  # Для кеширования
        self._docker_client = (
            docker.from_env() if docker and self._docker_available() else None
        )
        self._observer = None  # Для наблюдения за файлами
        self._template_files: Dict[str, str] = {}
        self._modified_files: Set[str] = set()

    def _start_watchdog(self, path: Path) -> None:
        """Start filesystem observer to track user edits."""
        self._modified_files = set()
        handler = _TemplateEditHandler(self, str(path))
        self._observer = Observer()
        self._observer.schedule(handler, str(path), recursive=True)
        try:
            self._observer.start()
        except Exception as e:
            logger.error(f"Failed to start observer: {e}")

    def _stop_watchdog(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    def _detect_project_type(self, path: Path) -> str:
        """Определяет тип проекта по его структуре."""
        files = {p.name.lower() for p in path.iterdir() if p.is_file()}
        dirs = {p.name.lower() for p in path.iterdir() if p.is_dir()}
        reqs_text = ""
        req_file = path / "requirements.txt"
        if req_file.exists():
            try:
                reqs_text = req_file.read_text().lower()
            except Exception:
                pass

        if (
            any(f.endswith(".ipynb") for f in files)
            or "notebooks" in dirs
            or "models" in dirs
            or any(lib in reqs_text for lib in ["torch", "tensorflow", "scikit-learn"])
        ):
            return "ML"
        if (
            "api" in dirs
            or "app.py" in files
            or any(
                framework in reqs_text for framework in ["flask", "fastapi", "django"]
            )
        ):
            return "API"
        if "cli.py" in files or "commands" in dirs or "__main__.py" in files:
            return "CLI"
        return "UNKNOWN"

    async def _activate_modules_for_project_type(self, project_type: str) -> None:
        """Автоматически загружает модули в зависимости от типа проекта."""
        if not hasattr(self.jarvis, "module_manager"):
            return
        mapping = {
            "CLI": ["voice_interface"],
            "API": ["sql_interface"],
            "ML": ["ml_trainer_seq2seq"],
        }
        for module in mapping.get(project_type.upper(), []):
            try:
                await self.jarvis.module_manager.load_module(module)
            except Exception as e:
                logger.error(f"Failed to load module {module}: {e}")

    def _load_project_history(self, path: Path) -> List[Dict[str, Any]]:
        """Загружает историю проекта из файла."""
        history_file = path / "project_history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.error("Failed to read project history")
        return []

    def _update_project_history(self, event: str = "open") -> None:
        """Обновляет историю работы с проектом и сохраняет ее в файл."""
        if not self.current_project:
            return
        path = Path(self.current_project["path"])
        history_file = path / "project_history.json"
        history = self._project_history
        history.append({"timestamp": datetime.now().isoformat(), "event": event})
        history = history[-self._MAX_HISTORY :]
        self._project_history = history
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write project history: {e}")

    async def _calculate_project_stats(self, path: Path) -> Dict[str, int]:
        """Подсчет простых статистик по проекту."""
        stats = {"files": 0, "lines": 0}
        for root, _, files in os.walk(path):
            for fname in files:
                stats["files"] += 1
                try:
                    with open(
                        Path(root) / fname, "r", encoding="utf-8", errors="ignore"
                    ) as f:
                        stats["lines"] += sum(1 for _ in f)
                except Exception:
                    continue
        return stats

    async def _detect_vcs_needed(self) -> bool:
        return False

    def _should_create_venv(self) -> bool:
        return False

    def _generate_ide_configs(self) -> None:
        pass

    def _docker_available(self) -> bool:
        if docker is None:
            return False
        try:
            docker.from_env().ping()
            return True
        except Exception:
            return False

    # ███████╗███████╗████████╗████████╗███████╗██████╗ ███████╗
    # ██╔════╝██╔════╝╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗██╔════╝
    # █████╗  ███████╗   ██║      ██║   █████╗  ██████╔╝███████╗
    # ██╔══╝  ╚════██║   ██║      ██║   ██╔══╝  ██╔══██╗╚════██║
    # ███████╗███████║   ██║      ██║   ███████╗██║  ██║███████║
    # ╚══════╝╚══════╝   ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝╚══════╝

    async def set_project(
        self,
        path: Union[str, Path],
        *,
        auto_init: bool = False,
        load_config: bool = True,
    ) -> bool:
        """Умная установка проекта с AI-анализом"""
        try:
            path = Path(path).absolute()

            if not path.exists():
                if auto_init:
                    return await self.create_project(
                        path, template=ProjectTemplateType.BASIC_PYTHON
                    )
                raise ProjectLifecycleException(f"Path not exists: {path}")

            await self._run_hooks("pre_set")

            project_data = await self._scan_project(path)
            self.current_project = project_data
            self._project_history = self._load_project_history(path)

            if load_config:
                await self.load_project_config()

            await self._analyze_project_intelligence()
            await self._activate_modules_for_project_type(
                project_data.get("type", "UNKNOWN")
            )
            self._update_project_history("open")
            await self._run_hooks("post_set")

            logger.info(f"Project activated: {project_data['name']}")
            return True

        except Exception as e:
            logger.error(f"Project activation failed: {e}", exc_info=True)
            await self._cleanup_on_failure()
            return False

    async def _scan_project(self, path: Path) -> Dict[str, Any]:
        """Глубокий анализ структуры проекта"""
        return {
            "name": path.name,
            "path": str(path),
            "system": platform.system(),
            "type": self._detect_project_type(path),
            "metadata": ProjectMetadata(),
            "intelligence": ProjectIntelligence(),
            "stats": await self._calculate_project_stats(path),
        }

    async def _analyze_project_intelligence(self) -> None:
        """AI-анализ кодовой базы"""
        if not self.current_project:
            return

        path = Path(self.current_project["path"])
        analyzer = CodeAnalyzer(path)
        self.current_project["intelligence"] = await analyzer.run_analysis()

        # Автодополнение тегов
        for tech in self.current_project["intelligence"].code_patterns:
            self.current_project["metadata"].tags.add(f"tech:{tech}")

    # ██████╗ ██████╗ ███████╗ █████╗ ████████╗███████╗
    # ██╔══██╗██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██╔════╝
    # ██████╔╝██████╔╝█████╗  ███████║   ██║   █████╗
    # ██╔═══╝ ██╔══██╗██╔══╝  ██╔══██║   ██║   ██╔══╝
    # ██║     ██║  ██║███████╗██║  ██║   ██║   ███████╗
    # ╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

    async def create_project(
        self,
        path: Union[str, Path],
        template: ProjectTemplateType = ProjectTemplateType.BASIC_PYTHON,
        **kwargs,
    ) -> bool:
        """Создание проекта с продвинутыми шаблонами"""
        try:
            await self._run_hooks("pre_create")

            path = Path(path).absolute()
            if path.exists():
                raise ProjectLifecycleException(f"Path already exists: {path}")

            path.mkdir(parents=True)
            await self._generate_template(template, path, **kwargs)

            # Инициализация проекта
            await self.set_project(path, auto_init=False)
            await self._init_project_infrastructure()

            await self._run_hooks("post_create")
            return True

        except Exception as e:
            logger.error(f"Project creation failed: {e}")
            await self._cleanup_on_failure()
            return False

    async def _generate_template(
        self, template: ProjectTemplateType, path: Path, **kwargs
    ) -> None:
        """Генерация структуры по шаблону с AI-дополнениями"""
        templates = {
            ProjectTemplateType.BASIC_PYTHON: [
                ("src/", None),
                (
                    "tests/",
                    {"__init__.py": "", "test_main.py": TEMPLATES["basic_test"]},
                ),
                ("docs/", None),
                (".env", "PYTHONPATH=src\n"),
                ("Dockerfile", TEMPLATES["dockerfile_python"]),
            ],
            # ... другие шаблоны
        }

        self._template_files = {}
        for item in templates.get(template, []):
            item_path, content = item
            full_path = path / item_path

            if content is None:
                full_path.mkdir()
            elif isinstance(content, dict):
                full_path.mkdir()
                for fname, fcontent in content.items():
                    target = full_path / fname
                    target.write_text(fcontent)
                    self._template_files[str(target.relative_to(path))] = fcontent
            else:
                full_path.write_text(content)
                self._template_files[str(full_path.relative_to(path))] = content

        self._start_watchdog(path)

    # ███████╗██╗   ██╗███╗   ██╗ ██████╗████████╗██╗ ██████╗ ███╗   ██╗
    # ██╔════╝██║   ██║████╗  ██║██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██║
    # █████╗  ██║   ██║██╔██╗ ██║██║        ██║   ██║██║   ██║██╔██╗ ██║
    # ██╔══╝  ██║   ██║██║╚██╗██║██║        ██║   ██║██║   ██║██║╚██╗██║
    # ██║     ╚██████╔╝██║ ╚████║╚██████╗   ██║   ██║╚██████╔╝██║ ╚████║
    # ╚═╝      ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝

    async def _init_project_infrastructure(self) -> None:
        """Автоматическая настройка окружения"""
        if not self.current_project:
            return

        path = Path(self.current_project["path"])

        # 1. Инициализация VCS
        if await self._detect_vcs_needed():
            subprocess.run(["git", "init"], cwd=path)

        # 2. Создание виртуального окружения
        if self._should_create_venv():
            subprocess.run(["python", "-m", "venv", "venv"], cwd=path)

        # 3. Генерация IDE конфигов
        self._generate_ide_configs()

        # 4. Docker-инициализация
        if (
            self._docker_client
            and self._docker_available()
            and (path / "Dockerfile").exists()
        ):
            self._docker_client.images.build(
                path=str(path), tag=f"{path.name.lower()}:latest"
            )

    async def close_project(self) -> bool:
        """Finalize project work and analyze modifications."""
        if not self.current_project:
            return False

        await self._run_hooks("pre_close")
        self._stop_watchdog()
        await self._capture_template_diffs()
        self._update_project_history("close")
        self.current_project = None
        await self._run_hooks("post_close")
        return True

    async def _capture_template_diffs(self) -> None:
        if not self._template_files:
            return
        project_path = Path(self.current_project["path"])
        diffs: Dict[str, str] = {}
        for rel, original in self._template_files.items():
            file_path = project_path / rel
            if file_path.exists():
                current = file_path.read_text()
                if current != original:
                    diff = "\n".join(
                        difflib.unified_diff(
                            original.splitlines(),
                            current.splitlines(),
                            fromfile=f"template/{rel}",
                            tofile=f"current/{rel}",
                            lineterm="",
                        )
                    )
                    diffs[rel] = diff
            else:
                diffs[rel] = "FILE REMOVED"

        if diffs:
            history = self.jarvis.memory.query("project_templates.history")
            if isinstance(history, dict):
                history = history.get("value")
            history = history or []
            history.append(
                {
                    "template": self.current_project.get("name", "unknown"),
                    "timestamp": datetime.now().isoformat(),
                    "diffs": diffs,
                }
            )
            self.jarvis.memory.remember(
                "project_templates.history", history, category="project"
            )

    def learn_template_updates(self, project_name: str) -> List[str]:
        """Apply user modifications from history to base templates."""
        history = self.jarvis.memory.query("project_templates.history")
        if isinstance(history, dict):
            history = history.get("value")
        if not history:
            return []

        updated: List[str] = []
        for entry in history:
            if entry.get("template") != project_name:
                continue
            for rel, diff in entry.get("diffs", {}).items():
                key = FILE_TO_TEMPLATE_KEY.get(rel)
                if not key or diff == "FILE REMOVED":
                    continue
                new_content = _apply_diff(TEMPLATES[key], diff)
                if new_content != TEMPLATES[key]:
                    TEMPLATES[key] = new_content
                    updated.append(key)
        return updated

    # ... (остальные методы из предыдущих реализаций с улучшениями)

    # ███████╗██╗  ██╗██████╗  ██████╗ ██╗  ██╗███████╗
    # ██╔════╝╚██╗██╔╝██╔══██╗██╔═══██╗██║ ██╔╝██╔════╝
    # █████╗   ╚███╔╝ ██████╔╝██║   ██║█████╔╝ ███████╗
    # ██╔══╝   ██╔██╗ ██╔═══╝ ██║   ██║██╔═██╗ ╚════██║
    # ███████╗██╔╝ ██╗██║     ╚██████╔╝██║  ██╗███████║
    # ╚══════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝

    def add_hook(self, hook_type: str, callback: Callable) -> None:
        """Добавление хука жизненного цикла"""
        if hook_type not in self._hooks:
            raise ValueError(
                f"Invalid hook type. Available: {list(self._hooks.keys())}"
            )
        self._hooks[hook_type].append(callback)

    async def _run_hooks(self, hook_type: str) -> None:
        """Асинхронный запуск хуков"""
        for hook in self._hooks.get(hook_type, []):
            try:
                if inspect.iscoroutinefunction(hook):
                    await hook(self)
                else:
                    hook(self)
            except Exception as e:
                logger.error(f"Hook '{hook_type}' failed: {e}")

    # ... (другие системные методы)


class CodeAnalyzer:
    """AI-анализатор кодовой базы проекта"""

    def __init__(self, project_path: Path):
        self.path = project_path
        self.tech_patterns = {
            "flask": (r"from flask import", 0.9),
            "django": (r"from django\.", 0.95),
            "pandas": (r"import pandas", 0.8),
        }

    async def run_analysis(self) -> ProjectIntelligence:
        """Запуск анализа с использованием ML-моделей"""
        result = ProjectIntelligence()

        # Анализ технологического стека
        for tech, (pattern, conf) in self.tech_patterns.items():
            if await self._search_in_files(pattern):
                result.code_patterns[tech] = conf

        # Расчет технического долга (упрощенный пример)
        result.tech_debt_score = await self._calculate_tech_debt()

        return result

    async def _search_in_files(self, pattern: str) -> bool:
        """Поиск паттернов в файлах проекта"""
        # Реализация с использованием aiofiles для асинхронного чтения
        # ...
        return False


TEMPLATES = {
    "basic_test": """import unittest\n\nclass TestBasic(unittest.TestCase):\n    def test_example(self):\n        self.assertTrue(True)""",
    "dockerfile_python": """FROM python:3.9\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD ["python", "./src/main.py"]""",
}

# Mapping of project file paths to template keys for learning
FILE_TO_TEMPLATE_KEY = {
    "tests/test_main.py": "basic_test",
    "Dockerfile": "dockerfile_python",
}


def _apply_diff(original: str, diff_text: str) -> str:
    """Apply unified diff to a text string using the patch library."""
    try:
        ps = patch.fromstring(diff_text.encode())
    except Exception as e:
        logger.error(f"Patch parse failed: {e}")
        return original
    with tempfile.TemporaryDirectory() as tmp:
        file_path = Path(tmp) / "file"
        file_path.write_text(original, encoding="utf-8")
        if not ps.apply(root=tmp):
            logger.error("Patch apply failed")
            return original
        return file_path.read_text(encoding="utf-8")
