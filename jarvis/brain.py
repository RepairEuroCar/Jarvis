# Directory structure to apply:
# jarvis/
# ├── __init__.py
# ├── jarvis.py         # entry point
# ├── brain.py
# ├── memory.py
# ├── nlu.py
# ├── processors.py
# ├── commands.py
# ├── modules.py
# ├── project.py
# └── utils.py

import ast
import difflib
import logging
import os
import tempfile
import time
import uuid

# jarvis/brain.py
from collections import deque
from pathlib import Path
from typing import Any, Dict, Type

from utils.linter import AstLinter
from utils.solution_compare import structural_diff

from .processors import (
    AnalyticalThoughtProcessor,
    APIBuilderProcessor,
    BaseThoughtProcessor,
    CreativeThoughtProcessor,
    LogicalThoughtProcessor,
    RefactorProcessor,
    TestGeneratorProcessor,
)

logger = logging.getLogger("Jarvis.Brain")


class ThoughtProcessorFactory:
    """Factory to create :class:`BaseThoughtProcessor` instances."""

    _registry: Dict[str, Type[BaseThoughtProcessor]] = {
        "logical": LogicalThoughtProcessor,
        "creative": CreativeThoughtProcessor,
        "analytical": AnalyticalThoughtProcessor,
        "refactor": RefactorProcessor,
        "test_generation": TestGeneratorProcessor,
        "api_builder": APIBuilderProcessor,
    }

    @classmethod
    def register(cls, name: str, processor_cls: Type[BaseThoughtProcessor]) -> None:
        """Register a new processor class."""
        cls._registry[name] = processor_cls

    @classmethod
    def create(cls, name: str, jarvis: Any = None) -> BaseThoughtProcessor:
        """Instantiate a processor by name."""
        processor_cls = cls._registry.get(name)
        if not processor_cls:
            raise ValueError(f"Unknown processor type: {name}")
        return processor_cls(jarvis=jarvis)


class Brain:
    """Central coordinator of reasoning logic.

    Thought processors are instantiated via :class:`ThoughtProcessorFactory` to
    allow easy extension and registration of new processors."""

    def __init__(self, jarvis):
        self.jarvis = jarvis
        self.working_memory = {}
        self.reasoning_history: deque = deque(maxlen=50)
        # Instantiate processors via the factory to decouple creation logic.
        self.thought_processors = {
            name: ThoughtProcessorFactory.create(name, jarvis=self.jarvis)
            for name in ThoughtProcessorFactory._registry
        }

    async def think(self, problem, context):
        problem_type = await self._classify_problem(problem, context)
        processor = self.thought_processors.get(
            problem_type, self.thought_processors["logical"]
        )
        self.working_memory.update(
            {"current_problem": problem, "current_context": context}
        )
        try:
            solution = await processor.process(problem, context)
        except Exception as e:
            solution = {
                "error": str(e),
                "status": "processing_failed",
                "processed_by": processor.__class__.__name__,
            }
        solution["problem_classification_used"] = problem_type

        plan = self._make_plan(problem, solution)
        code = self._generate_code(plan)

        solution["plan"] = plan
        solution["generated_code"] = code

        self.log_thoughts(problem, solution)
        self.working_memory.clear()
        return solution

    async def _classify_problem(self, problem, context):
        p = problem.lower()
        if any(x in p for x in ["проанализируй", "сравни", "статистика", "данные"]):
            return "analytical"
        if "рефактор" in p:
            return "refactor"
        if "тест" in p:
            return "test_generation"
        if "api" in p or "веб-сервис" in p:
            return "api_builder"
        if any(x in p for x in ["создай", "придумай", "идея"]):
            return "creative"
        if any(x in p for x in ["если", "как", "что если", "объясни"]):
            return "logical"
        return context.get("preferred_processor", "logical")

    def _update_long_term_memory(self, problem, solution):
        memory_key = f"brain.thoughts.{uuid.uuid5(uuid.NAMESPACE_DNS, problem).hex}"
        record = {
            "problem": problem,
            "solution": solution,
            "timestamp": time.time(),
        }
        self.jarvis.memory.remember(memory_key, record, category="reasoning")
        history = self.jarvis.memory.recall("brain.reasoning_history") or []
        history.append(record)
        if len(history) > 50:
            history = history[-50:]
        self.jarvis.memory.remember(
            "brain.reasoning_history", history, category="reasoning"
        )
        self.reasoning_history.append(record)

    def _make_plan(self, problem: str, solution: Dict[str, Any]) -> Dict[str, Any]:
        """Create a tiny plan based on the problem and solution."""
        return {"steps": [f"Разобрать задачу: {problem[:30]}", "Подготовить код"]}

    def _generate_code(self, plan: Dict[str, Any]) -> str:
        """Return placeholder code based on plan."""
        if not plan:
            return ""
        return "# code generated by Brain\n"

    def log_thoughts(self, task: str, result: Dict[str, Any]) -> None:
        """Persist reasoning outcome for later introspection."""
        self._update_long_term_memory(task, result)

    def get_chain_of_thought(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Return recent reasoning records."""
        return list(self.reasoning_history)[-limit:]

    def summarize_recent_thoughts(self, limit: int = 5) -> str:
        """Return a text summary of recent reasoning steps."""
        summaries = []
        for entry in self.get_chain_of_thought(limit=limit):
            problem = entry.get("problem", "")
            status = entry.get("solution", {}).get("status", "unknown")
            summaries.append(f"{problem[:50]} -> {status}")
        return "\n".join(summaries)

    def find_similar_solution(
        self, problem: str, threshold: float = 0.5
    ) -> Dict[str, Any] | None:
        """Return a stored solution for a similar problem if found.

        The method uses a very naive token overlap metric: the ratio of
        overlapping tokens to all unique tokens across the problems. If the
        best match score meets ``threshold`` the associated solution is
        returned, otherwise ``None`` is returned.
        """

        thoughts = self.jarvis.memory.query("brain.thoughts") or {}

        problem_tokens = set(problem.lower().split())
        best_score = 0.0
        best_record: Dict[str, Any] | None = None

        for entry in thoughts.values():
            record = entry.get("value") if isinstance(entry, dict) else entry
            stored_problem = str(record.get("problem", "")).lower()
            tokens = set(stored_problem.split())
            if not tokens:
                continue
            overlap = problem_tokens & tokens
            union = problem_tokens | tokens
            score = len(overlap) / len(union)
            if score > best_score:
                best_score = score
                best_record = record

        if best_record and best_score >= threshold:
            return best_record.get("solution")
        return None

    async def self_evolve(self, directory: str = ".") -> Dict[str, Any]:
        """Analyze and refactor Python files within a directory."""
        root = Path(directory)
        py_files = [p for p in root.rglob("*.py") if ".venv" not in str(p)]
        results: Dict[str, Any] = {}
        processor = self.thought_processors.get("refactor")
        for file_path in py_files:
            try:
                source = file_path.read_text(encoding="utf-8")
            except Exception as e:
                results[str(file_path)] = {"error": f"read_failed: {e}"}
                continue

            analysis = {"lines": len(source.splitlines()), "functions": 0, "classes": 0}
            try:
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        analysis["functions"] += 1
                    elif isinstance(node, ast.ClassDef):
                        analysis["classes"] += 1
            except Exception as e:
                analysis["parse_error"] = str(e)

            ref_result = await processor.process("refactor", {"source_code": source})
            new_code = ref_result.get("refactored_code", "")

            diff = "\n".join(
                difflib.unified_diff(
                    source.splitlines(),
                    new_code.splitlines(),
                    fromfile=str(file_path),
                    tofile=f"{file_path} (refactored)",
                )
            )
            results[str(file_path)] = {"analysis": analysis, "diff": diff}

        return results

    def self_review(self) -> Dict[str, Any]:
        """Lint recently generated code and return warnings.

        Additionally compares the structure of the latest code with any previous
        versions stored in ``reasoning_history`` and includes a structural diff
        when available.
        """
        linter = AstLinter()
        review: Dict[str, Any] = {}
        history = self.get_chain_of_thought(limit=5)
        for entry in history:
            code = entry.get("solution", {}).get("generated_code")
            if not code:
                continue
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
                tmp.write(code)
                tmp_path = tmp.name
            try:
                errors = linter.lint_file(tmp_path)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            if errors:
                review[entry["problem"]] = {
                    "warnings": [f"{e.lineno}: {e.message}" for e in errors]
                }

        diffs = self.compare_recent_code(limit=5)
        for problem, diff in diffs.items():
            review.setdefault(problem, {})["structural_diff"] = diff

        return review

    def compare_recent_code(self, limit: int = 5) -> Dict[str, str]:
        """Compare recent generated code snippets with past versions.

        The function searches the ``reasoning_history`` for earlier records of
        the same problem and returns unified diffs of the AST structures.
        """
        history = list(self.reasoning_history)
        diffs: Dict[str, str] = {}

        for idx in range(max(0, len(history) - limit), len(history)):
            entry = history[idx]
            problem = entry.get("problem")
            code = entry.get("solution", {}).get("generated_code")
            if not problem or not code:
                continue

            prev_code = None
            for past in reversed(history[:idx]):
                if past.get("problem") == problem:
                    prev_code = past.get("solution", {}).get("generated_code")
                    if prev_code:
                        break

            if prev_code:
                diff = structural_diff(prev_code, code)
                if diff:
                    diffs[problem] = diff

        return diffs
