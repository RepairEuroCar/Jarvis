# -----------------------------
# jarvis/processors/analytical.py
# -----------------------------
import asyncio
import re
import logging
from typing import Any, Dict, List, Union
from .base import BaseThoughtProcessor

logger = logging.getLogger("Jarvis.Processor.Analytical")

class AnalyticalThoughtProcessor(BaseThoughtProcessor):
    async def _extract_metrics(self, data: Union[str, Dict]) -> Dict[str, Any]:
        await asyncio.sleep(0.02)
        numbers = [int(n) for n in re.findall(r'\d+', str(data))]
        return {
            "count": len(numbers),
            "sum": sum(numbers),
            "average": sum(numbers)/len(numbers) if numbers else 0
        }

    async def _find_patterns(self, data: Union[str, Dict]) -> List[str]:
        await asyncio.sleep(0.02)
        patterns = []
        if "повтор" in str(data).lower():
            patterns.append("Обнаружен запрос на повторение.")
        if re.search(r'\d{4}', str(data)):
            patterns.append("Обнаружены числовые последовательности (возможно, даты).")
        return patterns or ["Паттернов не найдено."]

    async def _make_comparisons(self, data: Union[str, Dict]) -> Dict[str, str]:
        await asyncio.sleep(0.02)
        if "лучше" in str(data).lower() and "хуже" in str(data).lower():
            return {"comparison_type": "A vs B", "result": "Нужен детальный анализ."}
        return {"status": "Сравнений не произведено."}

    def _generate_recommendation(self, analysis: Dict[str, Any]) -> str:
        metrics = analysis.get("metrics", {})
        patterns = analysis.get("patterns", [])
        if metrics.get("sum", 0) > 100 and any("числовые последовательности" in p for p in patterns):
            return "Рекомендована визуализация больших числовых данных."
        elif patterns:
            return f"Проверьте паттерны: {'; '.join(patterns)}."
        return "Продолжайте мониторинг."

    async def process(self, problem: str, context: dict) -> dict:
        logger.info(f"AnalyticalProcessor обрабатывает: {problem[:50]}...")
        metrics, patterns, comparisons = await asyncio.gather(
            self._extract_metrics(problem),
            self._find_patterns(problem),
            self._make_comparisons(problem)
        )
        analysis = {
            "metrics": metrics,
            "patterns": patterns,
            "comparisons": comparisons
        }
        recommendation = self._generate_recommendation(analysis)
        return {
            "processed_by": self.__class__.__name__,
            "original_problem": problem,
            "analysis_type": "summary",
            "analysis": analysis,
            "recommendation": recommendation,
            "status": "completed"
        }

