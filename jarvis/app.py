import asyncio
import json
import os
import readline
import sys
import importlib
import traceback
from collections import defaultdict
import re
from typing import Any, Dict, List, Optional, Callable, Coroutine, Tuple, Union
import io
import contextlib
import datetime
import inspect
import logging
import platform
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import ast
from .event_queue import EventQueue
from jarvis.nlp.processor import NLUProcessor

# --- Конфигурация логгирования ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("jarvis.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Jarvis")

# --- Константы и перечисления ---
class CommandCategory(Enum):
    CORE = "Основные"
    MODULE = "Модули"
    SYSTEM = "Система"
    UTILITY = "Утилиты"
    DEVELOPMENT = "Разработка"
    PROJECT = "Проект"
    MEMORY = "Память"
    REASONING = "Рассуждения"

@dataclass
class CommandInfo:
    name: str
    description: str
    category: CommandCategory
    usage: str
    handler_name: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    is_async: bool = True
    requires_confirmation: bool = False

    def __post_init__(self):
        if not self.handler_name:
            self.handler_name = f"{self.name}_command"

# --- Мыслительные Процессоры ---
class BaseThoughtProcessor:
    async def process(self, problem: str, context: dict) -> dict:
        logger.info(f"Процессор {self.__class__.__name__} обрабатывает: {problem[:50]}...")
        await asyncio.sleep(0.05) # Уменьшено время для ускорения
        return {"processed_by": self.__class__.__name__, "original_problem": problem, "status": "placeholder_solution"}

class LogicalThoughtProcessor(BaseThoughtProcessor):
    async def process(self, problem: str, context: dict) -> dict:
        solution = await super().process(problem, context)
        solution["details"] = "Логический анализ выполнен. Найдены возможные шаги."
        # Пример: извлечение ключевых слов
        solution["keywords"] = re.findall(r'\b\w{4,}\b', problem.lower()) # слова длиннее 3 букв
        return solution

class CreativeThoughtProcessor(BaseThoughtProcessor):
    async def process(self, problem: str, context: dict) -> dict:
        solution = await super().process(problem, context)
        num_ideas = context.get("num_creative_ideas", 3) # Можно передавать параметры через контекст
        solution["ideas"] = [f"Креативная идея #{i+1} для '{problem[:20]}...'" for i in range(num_ideas)]
        solution["details"] = "Креативный штурм завершен. Предложены новаторские подходы."
        return solution

class AnalyticalThoughtProcessor(BaseThoughtProcessor): # Наследуемся от BaseThoughtProcessor
    async def _extract_metrics(self, problem_or_data: Union[str, Dict]) -> Dict[str, Any]:
        """Заглушка: Извлекает или вычисляет метрики из проблемы/данных."""
        logger.debug(f"AnalyticalProcessor: Извлечение метрик для '{str(problem_or_data)[:50]}...'")
        await asyncio.sleep(0.02)
        # Пример: если проблема содержит числа, считаем их сумму
        numbers = [int(n) for n in re.findall(r'\d+', str(problem_or_data))]
        return {"count": len(numbers), "sum": sum(numbers), "average": sum(numbers)/len(numbers) if numbers else 0}

    async def _find_patterns(self, problem_or_data: Union[str, Dict]) -> List[str]:
        """Заглушка: Ищет закономерности."""
        logger.debug(f"AnalyticalProcessor: Поиск паттернов для '{str(problem_or_data)[:50]}...'")
        await asyncio.sleep(0.02)
        patterns_found = []
        if "повтор" in str(problem_or_data).lower():
            patterns_found.append("Обнаружен запрос на повторение.")
        if len(re.findall(r'\d{4}', str(problem_or_data))) > 0: # Пример: найти 4-значные числа (годы?)
            patterns_found.append("Обнаружены числовые последовательности (возможно, даты/годы).")
        return patterns_found if patterns_found else ["Значимых паттернов не выявлено (заглушка)."]

    async def _make_comparisons(self, problem_or_data: Union[str, Dict]) -> Dict[str, str]:
        """Заглушка: Производит сравнения."""
        logger.debug(f"AnalyticalProcessor: Сравнение для '{str(problem_or_data)[:50]}...'")
        await asyncio.sleep(0.02)
        # Пример: если есть слова "лучше" или "хуже"
        if "лучше" in str(problem_or_data).lower() and "хуже" in str(problem_or_data).lower():
            return {"comparison_type": "A vs B", "result": "Требуется более детальный анализ для сравнения."}
        return {"status": "Сравнений не производилось (заглушка)."}

    def _generate_recommendation(self, analysis_results: Dict[str, Any]) -> str:
        """Заглушка: Генерирует рекомендацию на основе анализа."""
        logger.debug(f"AnalyticalProcessor: Генерация рекомендации на основе {list(analysis_results.keys())}")
        metrics = analysis_results.get("metrics", {})
        patterns = analysis_results.get("patterns", [])
        
        if metrics.get("sum", 0) > 100 and "Обнаружены числовые последовательности" in patterns:
            return "Рекомендация: Обнаружены значительные числовые данные. Рекомендуется их детальная проверка и визуализация."
        elif patterns:
            return f"Рекомендация: Обратите внимание на выявленные паттерны: {'; '.join(patterns)}. Возможно, это ключ к решению."
        return "Общая рекомендация: Продолжайте сбор данных и мониторинг ситуации (заглушка)."

    async def process(self, problem: str, context: dict) -> dict:
        """Анализирует данные и выявляет закономерности"""
        logger.info(f"AnalyticalProcessor обрабатывает: {problem[:50]}...")
        # Здесь мы можем передавать `problem` или какие-то данные из `context`
        # в аналитические функции. Для примера, передаем `problem`.
        
        # Имитируем, что анализ может занять некоторое время
        # и используем gather для параллельного (в данном случае псевдо) выполнения
        metrics_task = self._extract_metrics(problem)
        patterns_task = self._find_patterns(problem)
        comparisons_task = self._make_comparisons(problem)
        
        # Ждем завершения всех аналитических подзадач
        analysis_metrics, analysis_patterns, analysis_comparisons = await asyncio.gather(
            metrics_task, patterns_task, comparisons_task
        )
        
        analysis_summary = {
            "metrics": analysis_metrics,
            "patterns": analysis_patterns,
            "comparisons": analysis_comparisons
        }
        
        recommendation = self._generate_recommendation(analysis_summary)
        
        return {
            "processed_by": self.__class__.__name__, # Добавляем информацию о процессоре
            "original_problem": problem,
            "analysis_type": "analytical_summary", # Уточняем тип результата
            "analysis": analysis_summary,
            "recommendation": recommendation,
            "status": "analysis_completed"
        }

# --- Класс Мозга ---
class Brain:
    def __init__(self, jarvis_instance: Any): 
        self.jarvis = jarvis_instance
        self.working_memory: Dict[str, Any] = {} 
        self.thought_processors: Dict[str, BaseThoughtProcessor] = { 
            "logical": LogicalThoughtProcessor(),
            "creative": CreativeThoughtProcessor(),
            "analytical": AnalyticalThoughtProcessor() # Используем обновленный класс
        }
        logger.info("Мозг (Brain) инициализирован.")
        
    async def think(self, problem: str, context: dict) -> dict:
        logger.info(f"Мозг получил задачу: {problem[:100]}... с контекстом: {list(context.keys())}")
        
        problem_type = await self._classify_problem(problem, context)
        logger.info(f"Проблема классифицирована как: {problem_type}")
        
        processor = self.thought_processors.get(problem_type, self.thought_processors["logical"])
        logger.info(f"Выбран процессор: {processor.__class__.__name__}")
        
        self.working_memory['current_problem'] = problem 
        self.working_memory['current_context'] = context
        
        try:
            solution = await processor.process(problem, context)
            logger.info(f"Получено решение от {processor.__class__.__name__}")
        except Exception as e:
            logger.error(f"Ошибка в процессоре {processor.__class__.__name__}: {e}", exc_info=True)
            solution = {"error": str(e), "status": "processing_failed", "processed_by": processor.__class__.__name__}
        
        # Добавляем классификацию в само решение для удобства
        solution["problem_classification_used"] = problem_type
        self._update_long_term_memory(problem, solution)
        
        self.working_memory.clear() 
        return solution
    
    async def _classify_problem(self, problem: str, context: dict) -> str:
        problem_lower = problem.lower()
        # Приоритет для аналитики, если есть явные слова
        if "проанализируй" in problem_lower or "сравни" in problem_lower or \
           "оцени" in problem_lower or "статистика" in problem_lower or "данные по" in problem_lower:
            return "analytical"
        elif "создай" in problem_lower or "придумай" in problem_lower or "напиши" in problem_lower or \
             "сгенерируй" in problem_lower or "идея" in problem_lower:
            return "creative"
        elif "как" in problem_lower or "почему" in problem_lower or "что если" in problem_lower or \
             "объясни" in problem_lower or "план" in problem_lower: 
            return "logical"
        
        # Если в контексте есть указание на тип задачи
        if context.get("preferred_processor") in self.thought_processors:
            return context["preferred_processor"]
            
        return "logical" 
    
    def _update_long_term_memory(self, problem: str, solution: dict):
        problem_hash = uuid.uuid5(uuid.NAMESPACE_DNS, problem).hex 
        memory_key = f"brain.thoughts.{problem_hash}" 
        
        thought_record = {
            "problem": problem,
            "solution": solution, 
            "timestamp": time.time()
        }
        
        if self.jarvis.memory.remember(memory_key, thought_record, category="reasoning"):
            logger.info(f"Мысль по проблеме '{problem[:50]}...' сохранена (ключ: {memory_key}).")
        else:
            logger.warning(f"Не удалось сохранить мысль по проблеме '{problem[:50]}...'.")


class MemoryManager:
    def __init__(self, memory_file: str = "jarvis_memory.json"):
        self.memory_file = memory_file; self.memory: Dict[str, Any] = {}; self._initialize_memory()
    def _initialize_memory(self):
        base_structure = {"user_info": {"name": "User"}, "system": {}, "knowledge": {}, "temporal": {}}
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f: self.memory = json.load(f)
                for key in base_structure: self.memory.setdefault(key, base_structure[key])
            except Exception as e: logger.error(f"Ошибка загрузки памяти: {e}"); self.memory = base_structure
        else: self.memory = base_structure
    def save(self):
        try:
            if os.path.exists(self.memory_file): shutil.copy(self.memory_file, f"{self.memory_file}.bak.{int(time.time())}")
            with open(self.memory_file, "w", encoding="utf-8") as f: json.dump(self.memory, f, indent=2, ensure_ascii=False)
            logger.info("Память успешно сохранена")
        except Exception as e: logger.error(f"Ошибка сохранения памяти: {e}")
    def query(self, query: str) -> Any:
        try:
            parts = query.split("."); current = self.memory
            for part in parts:
                if part.startswith("[") and part.endswith("]"): current = current[int(part[1:-1])]
                else: current = current.get(part)
                if current is None: return None
            return current
        except Exception: return None
    def remember(self, key: str, value: Any, category: str = "general") -> bool:
        try:
            parts = key.split("."); current = self.memory
            for part in parts[:-1]: current = current.setdefault(part, {})
            current[parts[-1]] = {"value": value, "timestamp": time.time(), "category": category}
            return True
        except Exception as e: logger.error(f"Ошибка записи в память '{key}': {e}"); return False
    def forget(self, key: str) -> bool:
        try:
            parts = key.split("."); current = self.memory; parent = None; last_part = None
            for part in parts:
                if not isinstance(current, dict) or part not in current: return False
                parent = current; last_part = part; current = current[part]
            if parent and last_part and last_part in parent : del parent[last_part]; return True # Добавлена проверка last_part in parent
            return False
        except Exception: return False

class ModuleManager: 
    def __init__(self, jarvis_instance: Any): self.jarvis = jarvis_instance; self.modules: Dict[str, Any] = {}
    async def load_module(self, module_name: str, config: Optional[Dict] = None) -> bool:
        logger.info(f"Загрузка модуля {module_name} (заглушка)..."); return True
    async def unload_module(self, module_name: str) -> bool:
        logger.info(f"Выгрузка модуля {module_name} (заглушка)..."); return True

class ProjectManager: 
    def __init__(self, jarvis_instance: Any): self.jarvis = jarvis_instance; self.current_project: Optional[Dict[str, Any]] = None
    async def set_project(self, path: str) -> bool:
        self.current_project = {"name": os.path.basename(path), "path": path}; os.chdir(path)
        logger.info(f"Установлен проект: {self.current_project['name']}"); return True

class Jarvis:
    def __init__(self):
        self.memory = MemoryManager()
        self.nlu = NLUProcessor()
        self.module_manager = ModuleManager(self)
        self.project_manager = ProjectManager(self)
        self.brain = Brain(self) 

        self.is_running = False; self.start_time = time.time()
        self.command_history: List[Dict[str, Any]] = [] ; self.max_command_history = 100
        self.commands: Dict[str, Tuple[CommandInfo, Callable]] = {}
        self._register_core_commands()
        self.event_queue = EventQueue()
        self.event_listeners: Dict[str, List[Callable]] = self.event_queue._listeners
        self.user_name = self.memory.query("user_info.name") or "User"
        self.settings = self.memory.query("system.settings") or {"auto_save_memory": True}
        self.memory.remember("system.settings", self.settings) 
        saved_project_path = self.memory.query("system.projects.current_path")
        self._initial_project_path = saved_project_path if saved_project_path and os.path.isdir(saved_project_path) else None
        logger.info(f"Jarvis инициализирован для пользователя {self.user_name}")
    
    async def _initialize_project(self):
        if self._initial_project_path: await self.project_manager.set_project(self._initial_project_path)
        elif self.project_manager.current_project is None: await self.project_manager.set_project(os.getcwd())

    def _register_core_commands(self):
        core_command_infos = [
            CommandInfo(name="help", description="Показывает справку по командам.", category=CommandCategory.CORE, usage="help [команда]", aliases=["помощь", "справка"]),
            CommandInfo(name="exit", description="Завершает работу Jarvis.", category=CommandCategory.CORE, usage="exit", aliases=["quit", "выход"]),
            CommandInfo(name="create_python_function", description="Создает Python функцию с использованием AST.", category=CommandCategory.DEVELOPMENT, usage="create_python_function <сигнатура функции>", aliases=["создай_функцию_ast", "новая_функция_ast"]),
            CommandInfo(name="generate_large_python_file", description="Генерирует Python файл с большим количеством строк.", category=CommandCategory.DEVELOPMENT, usage="generate_large_python_file <путь_к_файлу.py> [число_строк]", aliases=["gen_long_py"]),
            CommandInfo(name="analyze_python_file", description="Анализирует Python файл.", category=CommandCategory.DEVELOPMENT, usage="analyze_python_file <путь_к_файлу.py>", aliases=["анализируй_py"]),
            CommandInfo(name="reason", description="Запускает Мозг для обдумывания проблемы.", category=CommandCategory.REASONING, usage="reason <описание проблемы>", aliases=["подумай", "обдумай_проблему"]),
            CommandInfo(name="load_module", description="Загружает модуль.", category=CommandCategory.SYSTEM, usage="load_module <имя_модуля>", aliases=["загрузи_модуль"]),
            CommandInfo(name="set_project", description="Устанавливает текущий проект.", category=CommandCategory.PROJECT, usage="set_project <путь_к_проекту>", aliases=["установи_проект"]),
            CommandInfo(name="update_template", description="Предлагает обновления шаблонов на основе истории изменений.", category=CommandCategory.PROJECT, usage="update_template <template_name>", aliases=["обнови_шаблон"]),
            CommandInfo(name="remember", description="Сохраняет информацию в память.", category=CommandCategory.MEMORY, usage="remember <ключ> <значение>", aliases=["запомни"]),
            CommandInfo(name="query_memory", description="Запрашивает информацию из памяти.", category=CommandCategory.MEMORY, usage="query_memory <ключ>", aliases=["спроси_память", "что_в_памяти"]),
            CommandInfo(name="forget", description="Удаляет информацию из памяти.", category=CommandCategory.MEMORY, usage="forget <ключ>", aliases=["забудь"]),
            CommandInfo(name="teach_pattern", description="Добавляет пользовательский NLU шаблон.", category=CommandCategory.DEVELOPMENT, usage="teach_pattern <intent> <trigger_phrase> [entity_type]", aliases=[]),
            CommandInfo(name="python_dsl", description="Преобразует фразу в код Python.", category=CommandCategory.DEVELOPMENT, usage="python_dsl <фраза>", aliases=["dsl_python"]),
            CommandInfo(name="parse_doc", description="Извлекает требования из описания.", category=CommandCategory.DEVELOPMENT, usage="parse_doc <текст>", aliases=["разбери_док"]),
            CommandInfo(name="self_learn", description="Запускает обучение Seq2Seq модели.", category=CommandCategory.DEVELOPMENT, usage="self_learn <trainer_id>", aliases=[]),
            CommandInfo(name="self_update", description="Коммитит изменения или делает pull.", category=CommandCategory.DEVELOPMENT, usage="self_update <commit|pull> [args]", aliases=[]),
        ]
        for cmd_info in core_command_infos:
            handler = getattr(self, cmd_info.handler_name or f"{cmd_info.name}_command")
            self.register_command(cmd_info, handler)
    
    def register_command(self, cmd_info: CommandInfo, handler: Callable):
        if not callable(handler): logger.error(f"Обработчик для '{cmd_info.name}' не callable."); return
        cmd_info.is_async = asyncio.iscoroutinefunction(handler)
        self.commands[cmd_info.name.lower()] = (cmd_info, handler)
        for alias in cmd_info.aliases: self.commands[alias.lower()] = (cmd_info, handler)
        logger.debug(f"Зарегистрирована команда: {cmd_info.name}")
    
    def unregister_command(self, command_name: str):
        command_name_lower = command_name.lower()
        if command_name_lower in self.commands:
            cmd_info, _ = self.commands.pop(command_name_lower)
            for alias in cmd_info.aliases:
                if alias.lower() in self.commands: del self.commands[alias.lower()]
            logger.debug(f"Удалена команда: {cmd_info.name}")

    async def publish_event(self, event_name: str, *args, priority: int = 0, **kwargs):
        logger.debug(f"Публикация события: {event_name} с {args}, {kwargs}, priority={priority}")
        await self.event_queue.emit(event_name, *args, priority=priority, **kwargs)

    def subscribe_event(self, event_name: str, listener: Callable):
        self.event_queue.subscribe(event_name, listener)
        logger.debug(f"Добавлен обработчик {listener.__name__} для {event_name}")

    async def add_background_task(self, coro: Coroutine, priority: int = 0) -> None:
        """Schedule a coroutine to run in background with optional priority."""
        await self.event_queue.add_task(coro, priority=priority)
    
    async def handle_user_input(self, text: str, source: str = "cli") -> Optional[str]:
        if not text.strip(): return None
        nlu_result = await self.nlu.process(text)
        command_name_from_nlu = nlu_result["intent"]
        entities = nlu_result["entities"]
        logger.info(f"NLU: intent='{command_name_from_nlu}', entities={entities}")
        self._log_command_to_history(nlu_result) 
        command_lookup = self.commands.get(command_name_from_nlu.lower())
        if not command_lookup:
            if command_name_from_nlu == "unknown_command" and nlu_result.get("raw_text"):
                 logger.info(f"Неизвестная команда, пробую передать '{nlu_result['raw_text'][:50]}...' в Мозг.")
                 return await self.reason_command(nlu_result['raw_text']) 
            return f"Неизвестная команда: '{command_name_from_nlu}'. Введите 'help'."
        cmd_info, handler = command_lookup
        actual_args = entities if cmd_info.name in ["create_python_function", "reason"] else entities.get("raw_args", "")
        if cmd_info.requires_confirmation and self.settings.get("confirm_destructive_actions", True):
            confirm = await self.ask_user(f"Подтвердите '{cmd_info.name}' (y/n): ")
            if confirm.lower() not in ["y", "yes", "да"]: return "Команда отменена."
        try:
            logger.info(f"Выполнение: {cmd_info.name} с {actual_args}")
            if cmd_info.is_async: result = await handler(actual_args)
            else: result = handler(actual_args)
            return str(result) if result is not None else "Команда выполнена."
        except Exception as e:
            logger.error(f"Ошибка выполнения {cmd_info.name}: {e}\n{traceback.format_exc()}")
            await self.publish_event("on_error", str(e))
            return f"Ошибка '{cmd_info.name}': {e}"
    
    def _log_command_to_history(self, nlu_result: Dict[str, Any]):
        if len(self.command_history) >= self.max_command_history: self.command_history.pop(0)
        self.command_history.append({"timestamp": time.time(), **nlu_result})
    
    async def ask_user(self, prompt: str) -> str:
        return await asyncio.to_thread(input, f"Jarvis ({self.user_name}): {prompt}")

    async def help_command(self, args_str: str) -> str:
        filter_name = args_str.strip().lower()
        if filter_name:
            lookup = self.commands.get(filter_name)
            if not lookup: return f"Команда '{filter_name}' не найдена."
            cmd_info, _ = lookup
            return f"Команда: {cmd_info.name} (Алиасы: {', '.join(cmd_info.aliases) or 'нет'})\nКатегория: {cmd_info.category.value}\nОписание: {cmd_info.description}\nИспользование: {cmd_info.usage}"
        output = ["Доступные команды ('help <команда>' для деталей):"]
        categorized_commands: Dict[CommandCategory, List[CommandInfo]] = defaultdict(list)
        unique_commands: Dict[str, CommandInfo] = {}
        for cmd_info_tuple in self.commands.values(): 
            cmd_info = cmd_info_tuple[0] # Берем CommandInfo из кортежа
            if cmd_info.name not in unique_commands: unique_commands[cmd_info.name] = cmd_info
        for cmd_info in sorted(unique_commands.values(), key=lambda ci: (ci.category.name, ci.name)):
            categorized_commands[cmd_info.category].append(cmd_info)
        for category, cmds_in_category in sorted(categorized_commands.items(), key=lambda item: item[0].name):
            output.append(f"\n--- {category.value} ---")
            for cmd_info in cmds_in_category: output.append(f"  {cmd_info.name.ljust(25)} - {cmd_info.description.splitlines()[0]}")
        return "\n".join(output)

    async def exit_command(self, args_str: str) -> str:
        await self.shutdown(); return "Завершение работы..."

    async def remember_command(self, args_str: str) -> str:
        parts = args_str.split(" ", 1);
        if len(parts) < 2: return "Использование: remember <ключ> <значение>"
        key, value_str = parts
        try: value = json.loads(value_str)
        except json.JSONDecodeError: value = value_str
        if self.memory.remember(key, value): return f"Запомнено: '{key}' -> '{value_str}'"
        return f"Не удалось запомнить '{key}'."

    async def query_memory_command(self, args_str: str) -> str:
        key = args_str.strip();
        if not key: return "Использование: query_memory <ключ>"
        result = self.memory.query(key)
        if result is not None:
            if isinstance(result, dict) and all(k in result for k in ["value", "timestamp"]):
                return f"'{key}': {json.dumps(result['value'], ensure_ascii=False, indent=2)} (Запомнено: {datetime.datetime.fromtimestamp(result['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}, Категория: {result.get('category', 'N/A')})"
            return f"'{key}': {json.dumps(result, ensure_ascii=False, indent=2)}"
        return f"Ключ '{key}' не найден в памяти."

    async def forget_command(self, args_str: str) -> str:
        key = args_str.strip();
        if not key: return "Использование: forget <ключ>"
        if self.memory.forget(key): return f"Забыто: '{key}'."
        return f"Не удалось забыть '{key}'."

    async def teach_pattern_command(self, args_str: str) -> str:
        parts = args_str.split(" ", 2)
        if len(parts) < 2:
            return "Использование: teach_pattern <intent> <trigger_phrase> [entity_type]"
        intent, trigger = parts[0].strip(), parts[1].strip()
        entity_type = parts[2].strip() if len(parts) > 2 else None
        self.nlu.add_pattern(intent, trigger, entity_type=entity_type, persist=True)
        return f"Паттерн для '{intent}' добавлен."

    async def python_dsl_command(self, args_str: str) -> str:
        phrase = args_str.strip()
        if not phrase:
            return "Использование: python_dsl <фраза>"
        from utils.python_dsl import phrase_to_python
        return phrase_to_python(phrase)

    async def parse_doc_command(self, args_str: str) -> str:
        text = args_str.strip()
        if not text:
            return "Использование: parse_doc <текст>"
        from utils.python_dsl import parse_technical_description
        parsed = parse_technical_description(text)
        return json.dumps(parsed, ensure_ascii=False, indent=2)

    def _parse_arg_string_to_ast(self, arg_str: str, arg_name: str) -> Optional[ast.expr]:
        try:
            if not arg_str: return None
            simple_types = {"int", "str", "bool", "float", "list", "dict", "tuple", "set", "Any", "None"}
            if arg_str in simple_types: return ast.Name(id=arg_str, ctx=ast.Load())
            match_list = re.fullmatch(r"List\[(.+)\]", arg_str, re.IGNORECASE)
            if match_list:
                inner_type_ast = self._parse_arg_string_to_ast(match_list.group(1).strip(), "inner_list_type")
                if inner_type_ast: return ast.Subscript(value=ast.Name(id="List", ctx=ast.Load()), slice=inner_type_ast, ctx=ast.Load())
            match_dict = re.fullmatch(r"Dict\[(.+),(.+)\]", arg_str, re.IGNORECASE)
            if match_dict:
                key_type_ast = self._parse_arg_string_to_ast(match_dict.group(1).strip(), "key_type")
                value_type_ast = self._parse_arg_string_to_ast(match_dict.group(2).strip(), "value_type")
                if key_type_ast and value_type_ast: return ast.Subscript(value=ast.Name(id="Dict", ctx=ast.Load()), slice=ast.Tuple(elts=[key_type_ast, value_type_ast], ctx=ast.Load()), ctx=ast.Load())
            if re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", arg_str):
                if '.' in arg_str:
                    parts = arg_str.split('.'); expr = ast.Name(id=parts[0], ctx=ast.Load())
                    for i in range(1, len(parts)): expr = ast.Attribute(value=expr, attr=parts[i], ctx=ast.Load())
                    return expr
                return ast.Name(id=arg_str, ctx=ast.Load())
            logger.warning(f"Не удалось распарсить тип '{arg_str}' для '{arg_name}'. Используется как Name.")
            return ast.Name(id=arg_str, ctx=ast.Load()) 
        except SyntaxError: logger.error(f"Ошибка парсинга типа '{arg_str}'."); return ast.Constant(value=arg_str)

    async def create_python_function_command(self, entities: Dict[str, Any]) -> str:
        raw_signature_str = entities.get("function_signature_raw", "").strip()
        if not raw_signature_str: return "Использование: create_python_function <имя_функции>[(аргументы)] [-> возвращаемый_тип]"
        name_match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)", raw_signature_str)
        if not name_match: return "Ошибка: Не удалось извлечь имя функции."
        func_name_str = name_match.group(1); remaining_signature = raw_signature_str[len(func_name_str):].strip()
        args_str_full = ""; return_type_str = "None"
        if "->" in remaining_signature: parts = remaining_signature.split("->", 1); args_str_full = parts[0].strip(); return_type_str = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "None"
        else: args_str_full = remaining_signature.strip()
        if args_str_full.startswith("(") and args_str_full.endswith(")"): args_str_full = args_str_full[1:-1].strip()
        ast_args_list = []; ast_defaults = []; imports_needed = set()
        if args_str_full:
            raw_args_list = re.split(r',(?![^\[]*\])(?![^\(]*\))(?![^\{]*\})', args_str_full)
            for arg_def_str in raw_args_list:
                arg_def_str = arg_def_str.strip();
                if not arg_def_str: continue
                name_part, type_part, default_part = "", None, None
                if "=" in arg_def_str: name_and_type, default_part_raw = arg_def_str.split("=", 1); default_part = default_part_raw.strip(); name_and_type = name_and_type.strip()
                else: name_and_type = arg_def_str
                if ":" in name_and_type: name_part, type_part_raw = name_and_type.split(":", 1); type_part = type_part_raw.strip(); name_part = name_part.strip()
                else: name_part = name_and_type.strip()
                arg_name_str = name_part; arg_type_ast = None
                if type_part:
                    arg_type_ast = self._parse_arg_string_to_ast(type_part, arg_name_str)
                    for el in ["List", "Dict", "Tuple", "Set", "Any", "Optional", "Union", "Callable"]:
                        if re.search(r'\b' + el + r'\b', type_part): imports_needed.add(f"from typing import {el}")
                if default_part:
                    try:
                        parsed_default_body = ast.parse(f"lambda: {default_part}").body[0]
                        if isinstance(parsed_default_body, ast.Expr) and isinstance(parsed_default_body.value, ast.Lambda): arg_default_ast = parsed_default_body.value.body
                        else: arg_default_ast = ast.Constant(value=default_part)
                    except SyntaxError: logger.warning(f"Ошибка парсинга значения по умолчанию '{default_part}' для '{arg_name_str}'."); arg_default_ast = ast.Constant(value=default_part)
                    ast_defaults.append(arg_default_ast)
                ast_args_list.append(ast.arg(arg=arg_name_str, annotation=arg_type_ast))
        return_annotation_ast = self._parse_arg_string_to_ast(return_type_str, "return_type")
        for el in ["List", "Dict", "Tuple", "Set", "Any", "Optional", "Union", "Callable"]:
            if re.search(r'\b' + el + r'\b', return_type_str): imports_needed.add(f"from typing import {el}")
        func_docstring = f"Функция {func_name_str}."; func_body = [ast.Expr(value=ast.Constant(value=func_docstring)), ast.Pass()]
        function_def_node = ast.FunctionDef(name=func_name_str, args=ast.arguments(posonlyargs=[], args=ast_args_list, vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=ast_defaults), body=func_body, decorator_list=[], returns=return_annotation_ast)
        import_nodes = []
        if imports_needed:
            grouped_imports = defaultdict(list)
            for imp_str in sorted(list(imports_needed)):
                match_from = re.match(r"from\s+([\w.]+)\s+import\s+([\w\s,]+)", imp_str)
                if match_from: grouped_imports[match_from.group(1)].extend([name.strip() for name in match_from.group(2).split(',')])
            for module_name, names_list in grouped_imports.items(): import_nodes.append(ast.ImportFrom(module=module_name, names=[ast.alias(name=n, asname=None) for n in sorted(list(set(names_list)))], level=0))
        module_nodes = import_nodes + ([ast.parse("\\n").body[0]] if import_nodes and function_def_node else []) + [function_def_node]
        module_ast = ast.Module(body=module_nodes, type_ignores=[])
        try: generated_code = ast.unparse(module_ast)
        except AttributeError:
            try: import astor; generated_code = astor.to_source(module_ast); logger.info("Использован 'astor'.")
            except ImportError: logger.error("'astor' не найден."); return "Ошибка: ast.unparse и 'astor' не найдены."
        await self.publish_event("python_code_generated", type="function", name=func_name_str, code=generated_code)
        return f"Сгенерирована функция '{func_name_str}' (AST):\n\n{generated_code}"

    async def generate_large_python_file_command(self, args_str: str) -> str:
        """Create a Python file with many simple lines for testing purposes."""
        parts = args_str.split()
        if not parts:
            return "Использование: generate_large_python_file <путь_к_файлу.py> [число_строк]"

        filepath = parts[0]
        try:
            num_lines = int(parts[1]) if len(parts) > 1 else 1000
        except ValueError:
            return "Ошибка: число строк должно быть целым"

        try:
            from utils.code_generator import generate_large_python_file
            abs_path = generate_large_python_file(filepath, num_lines)
        except Exception as e:
            logger.error(f"Ошибка генерации файла: {e}")
            return f"Ошибка генерации файла: {e}"
        await self.publish_event("python_code_generated", type="file", name=filepath, lines=num_lines)
        return f"Сгенерирован файл {abs_path} с {num_lines} строками кода"

    async def analyze_python_file_command(self, args_str: str) -> str:
        filepath_str = args_str.strip()
        if not filepath_str: return "Использование: analyze_python_file <путь_к_файлу.py>"
        if not os.path.exists(filepath_str) or not os.path.isfile(filepath_str): return f"Ошибка: Файл '{filepath_str}' не найден."
        if not filepath_str.lower().endswith(".py"): return f"Ошибка: Файл '{filepath_str}' не .py файл."
        try:
            with open(filepath_str, "r", encoding="utf-8") as f: source_code = f.read()
        except Exception as e: return f"Ошибка чтения '{filepath_str}': {e}"
        try: tree = ast.parse(source_code, filename=filepath_str)
        except SyntaxError as e: return f"Синтаксическая ошибка в '{filepath_str}' строка {e.lineno}, смещение {e.offset}:\n{e.text}"
        except Exception as e: return f"Ошибка парсинга '{filepath_str}': {e}"
        imports, functions, classes, async_functions = [], [], [], []
        for node in ast.iter_child_nodes(tree): 
            if isinstance(node, ast.Import): imports.extend([f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else "") for alias in node.names])
            elif isinstance(node, ast.ImportFrom): module_name = node.module or "."; names = ", ".join([alias.name + (f" as {alias.asname}" if alias.asname else "") for alias in node.names]); imports.append(f"from {'.' * node.level}{module_name} import {names}")
            elif isinstance(node, ast.FunctionDef): functions.append(f"{node.name}({', '.join([arg.arg for arg in node.args.args])}) (строка: {node.lineno})")
            elif isinstance(node, ast.AsyncFunctionDef): async_functions.append(f"{node.name}({', '.join([arg.arg for arg in node.args.args])}) (строка: {node.lineno})")
            elif isinstance(node, ast.ClassDef):
                methods, async_methods = [], []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef): methods.append(item.name)
                    elif isinstance(item, ast.AsyncFunctionDef): async_methods.append(item.name)
                class_info = f"{node.name} (строка: {node.lineno})"
                if methods: class_info += f" (методы: {', '.join(methods)})"
                if async_methods: class_info += f" (async методы: {', '.join(async_methods)})"
                classes.append(class_info)
        report = [f"Анализ файла: {filepath_str}\n"]
        if imports: report.append("Импорты:\n" + "\n".join([f"  - {imp}" for imp in sorted(list(set(imports)))])) 
        if functions: report.append("\nФункции:\n" + "\n".join([f"  - {func}" for func in functions]))
        if async_functions: report.append("\nАсинхронные функции:\n" + "\n".join([f"  - {func}" for func in async_functions]))
        if classes: report.append("\nКлассы:\n" + "\n".join([f"  - {cls}" for cls in classes]))
        if not any([imports, functions, classes, async_functions]): report.append("Значимых конструкций не найдено.")
        await self.publish_event("python_file_analyzed", filepath=filepath_str, analysis_result=report)
        return "\n".join(report)

    async def reason_command(self, entities_or_problem_str: Union[Dict[str, Any], str]) -> str:
        problem_description: str
        if isinstance(entities_or_problem_str, dict): 
            problem_description = entities_or_problem_str.get("problem_description_entity", "").strip()
        elif isinstance(entities_or_problem_str, str): 
            problem_description = entities_or_problem_str.strip()
        else: return "Ошибка: неверный формат аргумента для команды reason."
        if not problem_description: return "Пожалуйста, опишите проблему. Использование: reason <описание проблемы>"
        current_context = {
            "user_name": self.user_name, "current_timestamp": time.time(),
            "current_project": self.project_manager.current_project.get("name") if self.project_manager.current_project else "Нет",
        }
        await self.publish_event("brain_thinking_started", problem=problem_description, context_keys=list(current_context.keys()))
        solution = await self.brain.think(problem_description, current_context)
        await self.publish_event("on_thought", solution)
        await self.publish_event("brain_thinking_finished", problem=problem_description, solution_keys=list(solution.keys()))
        try: solution_str = json.dumps(solution, indent=2, ensure_ascii=False, default=str) 
        except TypeError: solution_str = str(solution) 
        return f"Результат обдумывания проблемы '{problem_description[:50]}...':\n{solution_str}"

    async def load_module_command(self, args_str: str) -> str:
        module_name = args_str.strip();
        if not module_name: return "Использование: load_module <имя_модуля>"
        if await self.module_manager.load_module(module_name): return f"Модуль '{module_name}' загружен."
        return f"Не удалось загрузить модуль '{module_name}'."

    async def set_project_command(self, args_str: str) -> str:
        project_path = args_str.strip();
        if not project_path: return "Использование: set_project <путь_к_проекту>"
        if await self.project_manager.set_project(project_path):
            if self.project_manager.current_project: self.memory.remember("system.projects.current_path", self.project_manager.current_project["path"])
            return f"Текущий проект: {self.project_manager.current_project.get('name', 'Ошибка') if self.project_manager.current_project else 'Ошибка'}"
        return f"Не удалось установить проект '{project_path}'."

    async def update_template_command(self, args_str: str) -> str:
        template_name = args_str.strip()
        if not template_name:
            return "Использование: update_template <template_name>"
        history = self.memory.query("project_templates.history")
        if isinstance(history, dict):
            history = history.get("value")
        if not history:
            return "История изменений шаблонов пуста."
        counts: Dict[str, int] = defaultdict(int)
        for entry in history:
            if entry.get("template") != template_name:
                continue
            for rel in entry.get("diffs", {}):
                counts[rel] += 1
        updated = self.project_manager.learn_template_updates(template_name)
        if updated:
            self.memory.remember("templates.last_updated", {"template": template_name, "files": updated})
            return "Обновлены шаблоны: " + ", ".join(updated)
        if not counts:
            return f"Нет записей для шаблона {template_name}."
        lines = [f"Изменения в {template_name}:"]
        for rel, c in counts.items():
            lines.append(f"{rel}: {c} модификаций")
        return "\n".join(lines)

    async def self_learn_command(self, args_str: str) -> str:
        module_name = "ml_trainer_seq2seq"
        if module_name not in self.module_manager.modules:
            if not await self.module_manager.load_module(module_name):
                return f"Не удалось загрузить модуль '{module_name}'."
        module = self.module_manager.modules.get(module_name)
        if hasattr(module, "start_training_command"):
            return await module.start_training_command(self, args_str)
        return "Команда обучения недоступна."

    async def self_update_command(self, args_str: str) -> str:
        parts = args_str.split(" ", 1)
        if not parts:
            return "Использование: self_update <commit|pull> [аргументы]"
        action = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        module_name = "git_manager"
        if module_name not in self.module_manager.modules:
            if not await self.module_manager.load_module(module_name):
                return f"Не удалось загрузить модуль '{module_name}'."
        git_module = self.module_manager.modules.get(module_name)
        if action == "commit":
            message = rest.strip() or "update"
            await git_module.commands["git_add"](self, ".")
            return await git_module.commands["git_commit"](self, f'"{message}"')
        if action == "pull":
            return await git_module.commands["git_pull"](self, rest)
        return "Использование: self_update <commit|pull> [аргументы]"

    async def interactive_loop(self):
        self.is_running = True
        await self.event_queue.start()
        await self._initialize_project()
        logger.info("Запуск интерактивного режима")
        await self.publish_event("on_start")
        print(f"\nJarvis vBrain (Python {platform.python_version()})"); print(f"Пользователь: {self.user_name}")
        if self.project_manager.current_project: print(f"Проект: {self.project_manager.current_project['name']}")
        print("Введите 'help' для команд, 'exit' для выхода\n")
        while self.is_running:
            try:
                p_name = os.path.basename(self.project_manager.current_project['path']) if self.project_manager.current_project else "~"
                prompt_text = f"[{self.user_name} @ {p_name}]> " # Добавлено prompt_text
                user_input = await asyncio.to_thread(sys.stdin.readline); user_input = user_input.strip() # Используем prompt_text
                if not user_input: continue
                if user_input.lower() in ["exit", "quit", "выход"]: await self.shutdown()
                if not self.is_running: break 
                result = await self.handle_user_input(user_input)
                if result:
                    print(f"\n{result}\n")
                    await self.publish_event("on_output", result)
            except KeyboardInterrupt: print("\nДля выхода введите 'exit' или Ctrl+D."); continue
            except EOFError:
                await self.shutdown()
                break
            except Exception as e:
                logger.error(f"Критическая ошибка в цикле: {e}\n{traceback.format_exc()}")
                await self.publish_event("on_error", str(e))
    
    async def shutdown(self):
        if not self.is_running: return
        logger.info("Завершение работы Jarvis...")
        self.is_running = False
        if self.settings.get("auto_save_memory", True):
            self.memory.save()
        await self.event_queue.stop()
        await self.publish_event("jarvis_shutdown")
        logger.info("Jarvis завершил работу.")
        print("\nJarvis завершил работу. До свидания!")

async def main(): 
    jarvis = None
    try: jarvis = Jarvis(); await jarvis.interactive_loop()
    except Exception as e: logger.critical(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        if jarvis and jarvis.is_running: logger.info("Аварийное завершение..."); await jarvis.shutdown() 
if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("Jarvis остановлен (KeyboardInterrupt в asyncio.run).")
    except Exception as e: logger.critical(f"Критическая ошибка верхнего уровня: {e}", exc_info=True)
    finally: print("Программа Jarvis полностью завершена.")

