# Directory structure to apply:
# jarvis/
# ├── __init__.py
# ├── jarvis.py         # entry point
# ├── brain.py
# ├── memory.py
# ├── nlu.py
# ├── processors.py
# ├── commands.py
# ├── modules.py
# ├── project.py
# └── utils.py

# jarvis/brain.py
from .processors import LogicalThoughtProcessor, CreativeThoughtProcessor, AnalyticalThoughtProcessor
from .memory.manager import MemoryManager
import logging, time, uuid

logger = logging.getLogger("Jarvis.Brain")

class Brain:
    def __init__(self, jarvis):
        self.jarvis = jarvis
        self.working_memory = {}
        self.thought_processors = {
            "logical": LogicalThoughtProcessor(),
            "creative": CreativeThoughtProcessor(),
            "analytical": AnalyticalThoughtProcessor()
        }

    async def think(self, problem, context):
        problem_type = await self._classify_problem(problem, context)
        processor = self.thought_processors.get(problem_type, self.thought_processors["logical"])
        self.working_memory.update({"current_problem": problem, "current_context": context})
        try:
            solution = await processor.process(problem, context)
        except Exception as e:
            solution = {"error": str(e), "status": "processing_failed", "processed_by": processor.__class__.__name__}
        solution["problem_classification_used"] = problem_type
        self._update_long_term_memory(problem, solution)
        self.working_memory.clear()
        return solution

    async def _classify_problem(self, problem, context):
        p = problem.lower()
        if any(x in p for x in ["проанализируй", "сравни", "статистика", "данные"]): return "analytical"
        if any(x in p for x in ["создай", "придумай", "идея"]): return "creative"
        if any(x in p for x in ["если", "как", "что если", "объясни"]): return "logical"
        return context.get("preferred_processor", "logical")

    def _update_long_term_memory(self, problem, solution):
        memory_key = f"brain.thoughts.{uuid.uuid5(uuid.NAMESPACE_DNS, problem).hex}"
        self.jarvis.memory.remember(memory_key, {
            "problem": problem,
            "solution": solution,
            "timestamp": time.time()
        }, category="reasoning")
