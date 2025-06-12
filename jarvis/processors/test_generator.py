import logging
from typing import Dict, Any
from .base import BaseThoughtProcessor

logger = logging.getLogger("Jarvis.Processor.TestGen")

class TestGeneratorProcessor(BaseThoughtProcessor):
    """Generates simple pytest style tests from a function name."""

    async def _process_logic(self, problem: str, context: Dict[str, Any]) -> Dict[str, Any]:
        fn_name = context.get("function_name") or problem.strip()
        test_code = (
            f"def test_{fn_name}():\n"
            f"    assert {fn_name}() is not None\n"
        )
        return {
            "processed_by": self.__class__.__name__,
            "original_problem": problem,
            "generated_test": test_code,
            "status": "completed",
        }
