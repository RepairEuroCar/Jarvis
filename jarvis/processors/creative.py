# -----------------------------
# jarvis/processors/creative.py
# -----------------------------
import logging

from .base import BaseThoughtProcessor

logger = logging.getLogger("Jarvis.Processor.Creative")


class CreativeThoughtProcessor(BaseThoughtProcessor):
    async def process(self, problem: str, context: dict) -> dict:
        logger.info(f"CreativeProcessor обрабатывает: {problem[:50]}...")
        solution = await super().process(problem, context)
        num_ideas = context.get("num_creative_ideas", 3)
        solution["ideas"] = [
            f"Идея #{i+1} для '{problem[:20]}...'" for i in range(num_ideas)
        ]
        solution["details"] = "Креативный штурм завершён."
        solution["status"] = "creative_completed"
        return solution
