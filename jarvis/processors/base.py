import asyncio
<<<<<<< HEAD
import logging
from typing import Any, Dict
=======
from typing import Any, Dict

from utils.logger import get_logger

logger = get_logger().getChild("Processor.Base")
>>>>>>> main



class BaseThoughtProcessor:
    def __init__(self, jarvis: Any = None):
        self.jarvis = jarvis

<<<<<<< HEAD
    async def process(
        self, problem: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
=======
    async def process(self, problem: str, context: Dict[str, Any]) -> Dict[str, Any]:
>>>>>>> main
        logger.info(f"Обработка: {problem[:50]}...")

        result = await self._process_logic(problem, context)

<<<<<<< HEAD
        if (
            context.get("is_voice")
            and self.jarvis
            and self.jarvis.voice_interface
        ):
=======
        if context.get("is_voice") and self.jarvis and self.jarvis.voice_interface:
>>>>>>> main
            await self._voice_feedback(result)

        return result

    async def _process_logic(
        self, problem: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Основная логика обработки (переопределяется в дочерних классах)"""
        await asyncio.sleep(0.05)
        return {
            "processed_by": self.__class__.__name__,
            "original_problem": problem,
            "status": "base_placeholder",
        }

    async def _voice_feedback(self, result: Dict[str, Any]):
        """Формирование голосового ответа"""
        response = self._extract_voice_response(result)
        if response:
            await self.jarvis.voice_interface.say_async(response)

    def _extract_voice_response(self, result: Dict[str, Any]) -> str:
        """Извлечение текста для голосового ответа"""
        if "conclusion" in result:
            return result["conclusion"][:100]
        elif "answer" in result:
            return result["answer"]
        return None
