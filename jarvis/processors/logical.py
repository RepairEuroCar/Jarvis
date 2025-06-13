import asyncio
import re
from typing import Any, Dict

from .base import BaseThoughtProcessor


class LogicalThoughtProcessor(BaseThoughtProcessor):
    async def _process_logic(
        self, problem: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        conclusion = await self._analyze_logic(problem)

        return {
            "processed_by": self.__class__.__name__,
            "original_problem": problem,
            "conclusion": conclusion,
            "status": "completed",
        }

    async def _analyze_logic(self, problem: str) -> str:
        """Анализ логических конструкций"""
        await asyncio.sleep(0.1)

        if "если" in problem.lower() and "то" in problem.lower():
            return self._process_condition(problem)

        return "Логический анализ выполнен"

    def _process_condition(self, problem: str) -> str:
        """Обработка условных конструкций"""
        match = re.search(r"если\s+(.*?)\s*то\s+(.*)", problem.lower())
        if match:
            condition, consequence = match.groups()
            return f"При условии '{condition.strip()}' следует '{consequence.strip()}'"
        return "Условная конструкция распознана"
