import ast
import asyncio
import logging
from typing import Dict, Any
from .base import BaseThoughtProcessor

logger = logging.getLogger("Jarvis.Processor.Refactor")

class RefactorProcessor(BaseThoughtProcessor):
    """Simplified refactoring processor that renames variables to snake_case."""

    async def _process_logic(self, problem: str, context: Dict[str, Any]) -> Dict[str, Any]:
        source = context.get("source_code", "")
        if not source:
            return {
                "processed_by": self.__class__.__name__,
                "original_problem": problem,
                "refactored_code": "",
                "status": "no_source_provided",
            }
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    node.id = node.id.lower()
            refactored = ast.unparse(tree)
        except Exception as e:
            logger.error(f"Refactoring error: {e}")
            return {
                "processed_by": self.__class__.__name__,
                "original_problem": problem,
                "error": str(e),
                "status": "failed",
            }
        return {
            "processed_by": self.__class__.__name__,
            "original_problem": problem,
            "refactored_code": refactored,
            "status": "completed",
        }
