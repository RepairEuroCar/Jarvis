import ast
import re
from typing import Any, Dict

from utils.logger import get_logger

from .base import BaseThoughtProcessor

try:
    import black
except Exception:  # pragma: no cover - black might be missing in tests
    black = None

logger = get_logger().getChild("Processor.Refactor")


class RefactorProcessor(BaseThoughtProcessor):
    """Simplified refactoring processor that renames variables to snake_case."""

    async def _process_logic(
        self, problem: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
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
                    node.id = self._to_snake_case(node.id)
            refactored = ast.unparse(tree)
            if black:
                refactored = black.format_str(refactored, mode=black.Mode())
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

    def _to_snake_case(self, name: str) -> str:
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
