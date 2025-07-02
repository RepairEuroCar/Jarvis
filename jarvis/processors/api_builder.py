import re
from typing import Any, Tuple

from utils.logger import get_logger

from .base import BaseThoughtProcessor

logger = get_logger().getChild("Processor.APIBuilder")


class APIBuilderProcessor(BaseThoughtProcessor):
    """Creates a small API skeleton using FastAPI from a text description."""

    def _parse_endpoints(self, text: str) -> list[Tuple[str, str]]:
        """Extract (METHOD, path) tuples from a description."""
        endpoints: list[Tuple[str, str]] = []
        for line in text.splitlines():
            match = re.search(r"(GET|POST|PUT|DELETE)\s+(/\S+)", line, re.I)
            if match:
                endpoints.append((match.group(1).upper(), match.group(2)))
        return endpoints

    async def _process_logic(
        self, problem: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        description = context.get("api_description") or problem
        endpoints = self._parse_endpoints(description)
        if not endpoints:
            endpoint = context.get("endpoint", "/")
            endpoints = [("GET", endpoint)]

        code_lines = ["from fastapi import FastAPI", "", "app = FastAPI()", ""]
        for method, path in endpoints:
            func_name = path.strip("/").replace("/", "_") or "root"
            code_lines.append(f"@app.{method.lower()}('{path}')")
            code_lines.append(f"async def {func_name}():")
            code_lines.append(f"    return {{'message': '{func_name}'}}")
            code_lines.append("")
        code = "\n".join(code_lines).strip()

        return {
            "processed_by": self.__class__.__name__,
            "original_problem": problem,
            "api_code": code,
            "status": "completed",
        }
