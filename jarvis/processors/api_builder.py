import logging
from typing import Dict, Any
from .base import BaseThoughtProcessor

logger = logging.getLogger("Jarvis.Processor.APIBuilder")

class APIBuilderProcessor(BaseThoughtProcessor):
    """Creates a small API skeleton using FastAPI."""

    async def _process_logic(self, problem: str, context: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = context.get("endpoint", "/")
        code = (
            "from fastapi import FastAPI\n\n"
            "app = FastAPI()\n\n"
            f"@app.get('{endpoint}')\n"
            "async def root():\n"
            "    return {'message': 'hello'}\n"
        )
        return {
            "processed_by": self.__class__.__name__,
            "original_problem": problem,
            "api_code": code,
            "status": "completed",
        }
