import ast
import inspect
import re
from typing import Any, Dict, List, Tuple

from .base import BaseThoughtProcessor
from utils.logger import get_logger

logger = get_logger().getChild("Processor.TestGen")


class TestGeneratorProcessor(BaseThoughtProcessor):
    """Generates pytest tests from function docstrings or name."""

    def _extract_examples(self, doc: str) -> List[Tuple[str, str]]:
        """Return list of (expression, expected) pairs from doctest examples."""
        examples: List[Tuple[str, str]] = []
        lines = inspect.cleandoc(doc).splitlines()
        for i, line in enumerate(lines):
            m = re.match(r">>>\s*(.+)", line)
            if m and i + 1 < len(lines):
                expr = m.group(1)
                expected = lines[i + 1].strip()
                examples.append((expr, expected))
        return examples

    async def _process_logic(
        self, problem: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        fn_name = context.get("function_name") or problem.strip()
        source = context.get("source_code", "")
        tests: List[str] = []

        if source:
            try:
                tree = ast.parse(source)
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                        doc = ast.get_docstring(node)
                        if doc:
                            for expr, expected in self._extract_examples(doc):
                                tests.append(f"assert {expr} == {expected}")
                        break
            except Exception as e:
                logger.error(f"Docstring parsing error: {e}")

        if not tests:
            tests.append(f"assert {fn_name}() is not None")

        body = "\n    ".join(tests)
        test_code = f"def test_{fn_name}():\n    {body}\n"

        return {
            "processed_by": self.__class__.__name__,
            "original_problem": problem,
            "generated_test": test_code,
            "status": "completed",
        }
