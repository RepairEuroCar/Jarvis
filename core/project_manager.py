# -----------------------------
# jarvis/core/project_manager.py
# -----------------------------
import os
import logging
import subprocess
import importlib
import shutil
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List, Set, Union, Callable, Coroutine
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
import platform
import inspect
import aiofiles
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import difflib
import difflib
import aioredis
import docker
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter

logger = logging.getLogger("Jarvis.ProjectManager")

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
            'pre_create': [], 'post_create': [],
            'pre_close': [], 'post_close': []
        }
        self._redis = None  # Для кеширования
        self._docker_client = docker.from_env() if self._docker_available() else None
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

    # ███████╗███████╗████████╗████████╗███████╗██████╗ ███████╗
    # ██╔════╝██╔════╝╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗██╔════╝
    # █████╗  ███████╗   ██║      ██║   █████╗  ██████╔╝███████╗
    # ██╔══╝  ╚════██║   ██║      ██║   ██╔══╝  ██╔══██╗╚════██║
    # ███████╗███████║   ██║      ██║   ███████╗██║  ██║███████║
    # ╚══════╝╚══════╝   ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝╚══════╝

    async def set_project(self, path: Union[str, Path], *, 
                        auto_init: bool = False, 
                        load_config: bool = True) -> bool:
        """Умная установка проекта с AI-анализом"""
        try:
            path = Path(path).absolute()
            
            if not path.exists():
                if auto_init:
                    return await self.create_project(path, template=ProjectTemplateType.BASIC_PYTHON)
                raise ProjectLifecycleException(f"Path not exists: {path}")

            await self._run_hooks('pre_set')
            
            project_data = await self._scan_project(path)
            self.current_project = project_data
            
            if load_config:
                await self.load_project_config()
            
            await self._analyze_project_intelligence()
            self._update_project_history()
            await self._run_hooks('post_set')
            
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
            "metadata": ProjectMetadata(),
            "intelligence": ProjectIntelligence(),
            "stats": await self._calculate_project_stats(path)
        }

    async def _analyze_project_intelligence(self) -> None:
        """AI-анализ кодовой базы"""
        if not self.current_project:
            return
            
        path = Path(self.current_project['path'])
        analyzer = CodeAnalyzer(path)
        self.current_project['intelligence'] = await analyzer.run_analysis()
        
        # Автодополнение тегов
        for tech in self.current_project['intelligence'].code_patterns:
            self.current_project['metadata'].tags.add(f"tech:{tech}")

    # ██████╗ ██████╗ ███████╗ █████╗ ████████╗███████╗
    # ██╔══██╗██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██╔════╝
    # ██████╔╝██████╔╝█████╗  ███████║   ██║   █████╗  
    # ██╔═══╝ ██╔══██╗██╔══╝  ██╔══██║   ██║   ██╔══╝  
    # ██║     ██║  ██║███████╗██║  ██║   ██║   ███████╗
    # ╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

    async def create_project(self, path: Union[str, Path], 
                           template: ProjectTemplateType = ProjectTemplateType.BASIC_PYTHON,
                           **kwargs) -> bool:
        """Создание проекта с продвинутыми шаблонами"""
        try:
            await self._run_hooks('pre_create')
            
            path = Path(path).absolute()
            if path.exists():
                raise ProjectLifecycleException(f"Path already exists: {path}")

            path.mkdir(parents=True)
            await self._generate_template(template, path, **kwargs)
            
            # Инициализация проекта
            await self.set_project(path, auto_init=False)
            await self._init_project_infrastructure()
            
            await self._run_hooks('post_create')
            return True
            
        except Exception as e:
            logger.error(f"Project creation failed: {e}")
            await self._cleanup_on_failure()
            return False

    async def _generate_template(self, template: ProjectTemplateType, path: Path, **kwargs) -> None:
        """Генерация структуры по шаблону с AI-дополнениями"""
        templates = {
            ProjectTemplateType.BASIC_PYTHON: [
                ("src/", None),
                ("tests/", {"__init__.py": "", "test_main.py": TEMPLATES["basic_test"]}),
                ("docs/", None),
                (".env", "PYTHONPATH=src\n"),
                ("Dockerfile", TEMPLATES["dockerfile_python"])
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
            
        path = Path(self.current_project['path'])
        
        # 1. Инициализация VCS
        if await self._detect_vcs_needed():
            subprocess.run(["git", "init"], cwd=path)
        
        # 2. Создание виртуального окружения
        if self._should_create_venv():
            subprocess.run(["python", "-m", "venv", "venv"], cwd=path)
        
        # 3. Генерация IDE конфигов
        self._generate_ide_configs()
        
        # 4. Docker-инициализация
        if self._docker_available() and (path / "Dockerfile").exists():
            self._docker_client.images.build(path=str(path), tag=f"{path.name.lower()}:latest")

    async def close_project(self) -> bool:
        """Finalize project work and analyze modifications."""
        if not self.current_project:
            return False

        await self._run_hooks('pre_close')
        self._stop_watchdog()
        await self._capture_template_diffs()
        self.current_project = None
        await self._run_hooks('post_close')
        return True

    async def _capture_template_diffs(self) -> None:
        if not self._template_files:
            return
        project_path = Path(self.current_project['path'])
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
            self.jarvis.memory.remember("project_templates.history", history, category="project")

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
            raise ValueError(f"Invalid hook type. Available: {list(self._hooks.keys())}")
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
            'flask': (r'from flask import', 0.9),
            'django': (r'from django\.', 0.95),
            'pandas': (r'import pandas', 0.8)
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
    "dockerfile_python": """FROM python:3.9\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD ["python", "./src/main.py"]"""
}