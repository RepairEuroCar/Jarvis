# -----------------------------
# jarvis/nlu/processor.py
# -----------------------------
import asyncio
import difflib
import logging
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..commands.registry import CommandCategory

# TODO: Развитие интеллекта задач
#  - Распознавание семантики задач: генерация, анализ, перевод, диагностика
#  - Автоопределение intent + confidence
#  - Ответ на естественные вопросы: «Как ты решил это?»

logger = logging.getLogger("Jarvis.NLU")


class EntityExtractionMode(Enum):
    ALL_AFTER_TRIGGER = auto()
    NO_ARGS = auto()
    NAMED_ENTITIES = auto()


class TaskSemantics(Enum):
    GENERATION = "generation"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    DIAGNOSTICS = "diagnostics"
    UNKNOWN = "unknown"


@dataclass
class CommandPattern:
    intent: str
    triggers: List[str]
    entity_extraction_mode: EntityExtractionMode
    entity_names: List[str] = field(default_factory=list)
    category: CommandCategory = CommandCategory.UTILITY
    description: str = ""
    min_confidence: float = 0.9


@dataclass
class ProcessingResult:
    intent: str
    entities: Dict[str, Any]
    confidence: float
    raw_text: str
    category: CommandCategory
    is_repeated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    semantics: TaskSemantics = TaskSemantics.UNKNOWN


class NLUProcessor:
    def __init__(
        self, memory_manager: Optional[Any] = None, max_history_size: int = 100
    ):
        self.memory_manager = memory_manager
        self.command_patterns: List[CommandPattern] = (
            self._initialize_command_patterns()
        )
        self.context: Dict[str, Any] = {}
        self.history: deque[ProcessingResult] = deque(maxlen=max_history_size)
        self.entity_patterns: Dict[str, str] = {
            "path_entity": r"(?:[a-zA-Z]:)?(?:[/\\][^/\\]*)+/?",
            "module_name_entity": r"[a-zA-Z_][a-zA-Z0-9_]*",
            "function_name_entity": r"[a-zA-Z_][a-zA-Z0-9_]*",
            "class_name_entity": r"[A-Z_][a-zA-Z0-9_]*",
            "python_var_entity": r"[a-zA-Z_][a-zA-Z0-9_]*",
            "number_entity": r"\d+",
            "string_entity": r"\"[^\"]*\"|\'[^\']*\'",
            "filename_entity": r"[\w\.-]+",
            "problem_description_entity": r".+",
        }
        self._compiled_entity_patterns = {
            name: re.compile(pattern) for name, pattern in self.entity_patterns.items()
        }

        self.semantics_keywords = {
            TaskSemantics.GENERATION: ["создай", "сгенерируй", "generate", "напиши"],
            TaskSemantics.ANALYSIS: ["анализ", "проанализируй", "analyze"],
            TaskSemantics.TRANSLATION: ["переведи", "translate"],
            TaskSemantics.DIAGNOSTICS: ["диагност", "ошибка", "diagnose"],
        }

        self.learned_corrections: Dict[str, str] = {}
        if self.memory_manager:
            self._load_custom_patterns()
            self.learned_corrections = (
                self.memory_manager.recall("nlu.corrections") or {}
            )

    def _detect_task_semantics(self, text_lower: str) -> TaskSemantics:
        for sem, words in self.semantics_keywords.items():
            for w in words:
                if w in text_lower:
                    return sem
        return TaskSemantics.UNKNOWN

    def _initialize_command_patterns(self) -> List[CommandPattern]:
        return [
            CommandPattern(
                intent="reason_about_problem",
                triggers=["reason about", "подумай над", "реши проблему"],
                entity_extraction_mode=EntityExtractionMode.ALL_AFTER_TRIGGER,
                entity_names=["problem_description_entity"],
                category=CommandCategory.REASONING,
                description="Запускает Мозг для решения проблемы.",
                min_confidence=0.95,
            ),
            CommandPattern(
                intent="exit",
                triggers=["exit", "quit", "выйти"],
                entity_extraction_mode=EntityExtractionMode.NO_ARGS,
                category=CommandCategory.CORE,
                description="Выход из Jarvis.",
            ),
            CommandPattern(
                intent="create_class",
                triggers=["create class", "создай класс", "напиши класс"],
                entity_extraction_mode=EntityExtractionMode.ALL_AFTER_TRIGGER,
                entity_names=["class_name_entity"],
                category=CommandCategory.DEVELOPMENT,
                description="Создает каркас класса",
            ),
            CommandPattern(
                intent="generate_test",
                triggers=["generate test", "создай тест", "напиши тест"],
                entity_extraction_mode=EntityExtractionMode.ALL_AFTER_TRIGGER,
                entity_names=["function_name_entity"],
                category=CommandCategory.DEVELOPMENT,
                description="Генерирует тест",
            ),
            CommandPattern(
                intent="build_api",
                triggers=["build api", "создай api", "создай веб-сервис"],
                entity_extraction_mode=EntityExtractionMode.ALL_AFTER_TRIGGER,
                entity_names=["path_entity"],
                category=CommandCategory.DEVELOPMENT,
                description="Создает API шаблон",
            ),
            CommandPattern(
                intent="explain_solution",
                triggers=["как ты решил это", "как ты это решил", "объясни решение"],
                entity_extraction_mode=EntityExtractionMode.NO_ARGS,
                category=CommandCategory.REASONING,
                description="Объясняет процесс решения последней задачи",
            ),
        ]

    async def process(self, text: str) -> Dict[str, Any]:
        """Основной метод обработки входящего текста."""
        text_original = text.strip()
        if not text_original:
            return self._create_fallback_result("empty_input", text_original)

        text_lower = text_original.lower()

        if text_lower == "повтори" and self.history:
            result = self._handle_repeat_command()
        else:
            result = await self._process_text(text_original, text_lower)
        if isinstance(result, ProcessingResult):
            return result.__dict__
        return result

    async def _process_text(
        self, text_original: str, text_lower: str
    ) -> ProcessingResult:
        """Обрабатывает текст, пытаясь сопоставить с известными шаблонами команд."""
        if text_lower in self.learned_corrections:
            intent = self.learned_corrections[text_lower]
            pattern = CommandPattern(
                intent=intent,
                triggers=[text_lower],
                entity_extraction_mode=EntityExtractionMode.NO_ARGS,
                description="Learned correction",
            )
            result = await self._extract_entities(pattern, text_original, text_lower, 1.0)
            self._update_history(result)
            return result
        for pattern in self.command_patterns:
            if result := await self._match_pattern(pattern, text_original, text_lower):
                self._update_history(result)
                return result

        return self._handle_fallback(text_original)

    async def _match_pattern(
        self, pattern: CommandPattern, text_original: str, text_lower: str
    ) -> Optional[ProcessingResult]:
        """Пытается сопоставить текст с конкретным шаблоном команды."""
        for trigger in pattern.triggers:
            if text_lower.startswith(trigger.lower()):
                return await self._extract_entities(
                    pattern, text_original, trigger, 1.0
                )
            ratio = difflib.SequenceMatcher(None, text_lower, trigger.lower()).ratio()
            if ratio > 0.75:
                return await self._extract_entities(
                    pattern, text_original, trigger, ratio
                )
        return None

    async def _extract_entities(
        self, pattern: CommandPattern, text: str, trigger: str, confidence: float
    ) -> ProcessingResult:
        """Извлекает сущности из текста в соответствии с шаблоном."""
        args_part = text[len(trigger) :].strip()
        entities = {"raw_args": args_part}

        if pattern.entity_extraction_mode == EntityExtractionMode.ALL_AFTER_TRIGGER:
            if pattern.entity_names:
                entities[pattern.entity_names[0]] = args_part

        return ProcessingResult(
            intent=pattern.intent,
            entities=entities,
            confidence=max(confidence, pattern.min_confidence),
            raw_text=text,
            category=pattern.category,
            metadata={"trigger": trigger},
            semantics=self._detect_task_semantics(text.lower()),
        )

    def _update_history(self, result: ProcessingResult) -> None:
        """Обновляет историю обработки команд."""
        self.history.append(result)

    def _handle_repeat_command(self) -> ProcessingResult:
        """Обрабатывает команду повторения последнего действия."""
        last_result = self.history[-1]
        return ProcessingResult(
            **{**last_result.__dict__, "is_repeated": True, "confidence": 1.0}
        )

    def _handle_fallback(self, text: str) -> ProcessingResult:
        """Обрабатывает текст, который не соответствует ни одному шаблону."""
        parts = text.split(maxsplit=1)
        result = self._create_fallback_result(
            parts[0].lower() if parts else "unknown_command",
            text,
            parts[1] if len(parts) > 1 else "",
            semantics=self._detect_task_semantics(text.lower()),
        )
        self._update_history(result)
        return result

    def _create_fallback_result(
        self,
        intent: str,
        raw_text: str,
        raw_args: str = "",
        semantics: TaskSemantics = TaskSemantics.UNKNOWN,
    ) -> ProcessingResult:
        """Создает результат обработки для неизвестных команд."""
        return ProcessingResult(
            intent=intent,
            entities={"raw_args": raw_args},
            confidence=0.3,
            raw_text=raw_text,
            category=CommandCategory.UTILITY,
            metadata={"is_fallback": True},
            semantics=semantics,
        )

    async def process_stream(
        self, text_stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[ProcessingResult, None]:
        """Обрабатывает поток текстовых команд."""
        async for text in text_stream:
            yield await self.process(text)

    def add_pattern(
        self,
        intent: str,
        trigger: str,
        entity_type: Optional[str] = None,
        persist: bool = False,
    ) -> None:
        """Добавляет новый шаблон распознавания команд."""
        pattern = CommandPattern(
            intent=intent,
            triggers=[trigger],
            entity_extraction_mode=(
                EntityExtractionMode.ALL_AFTER_TRIGGER
                if entity_type
                else EntityExtractionMode.NO_ARGS
            ),
            entity_names=[entity_type] if entity_type else [],
            description="User taught pattern",
        )
        self.command_patterns.append(pattern)
        if persist and self.memory_manager:
            existing = self.memory_manager.recall("nlu.custom_patterns") or []
            existing.append(
                {
                    "intent": intent,
                    "triggers": [trigger],
                    "entity_extraction_mode": pattern.entity_extraction_mode.name,
                    "entity_names": [entity_type] if entity_type else [],
                }
            )
            self.memory_manager.remember("nlu.custom_patterns", existing)
            self.memory_manager.save()

    def learn_correction(self, wrong_text: str, intent: str, persist: bool = False) -> None:
        """Запоминает исправление неверно распознанной команды."""
        self.learned_corrections[wrong_text.lower()] = intent
        if persist and self.memory_manager:
            self.memory_manager.remember("nlu.corrections", self.learned_corrections)
            self.memory_manager.save()

    def _load_custom_patterns(self) -> None:
        """Загружает сохраненные пользователем шаблоны из памяти."""
        stored = self.memory_manager.recall("nlu.custom_patterns") or []
        for pat in stored:
            try:
                mode = EntityExtractionMode[
                    pat.get("entity_extraction_mode", "NO_ARGS")
                ]
                cp = CommandPattern(
                    intent=pat["intent"],
                    triggers=pat.get("triggers", []),
                    entity_extraction_mode=mode,
                    entity_names=pat.get("entity_names", []),
                    description="User taught pattern",
                )
                self.command_patterns.append(cp)
            except Exception as e:
                logger.error(f"Ошибка загрузки пользовательского паттерна: {e}")

        corrections = self.memory_manager.recall("nlu.corrections") or {}
        self.learned_corrections.update({k.lower(): v for k, v in corrections.items()})
