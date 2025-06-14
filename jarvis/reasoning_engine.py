import logging
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, List

logger = logging.getLogger("Jarvis.ReasoningEngine")


@dataclass
class Step:
    stage: str
    data: Any


class ReasoningEngine:
    """Primitive chain-of-thought reasoning engine."""

    def __init__(self) -> None:
        self.logger = logger

    def _generate_hypotheses(self, goal: str) -> List[str]:
        if "ssh" in goal.lower():
            return ["~/.ssh", "/etc/ssh"]
        return []

    def _build_plan(self, hypotheses: List[str]) -> List[str]:
        if not hypotheses:
            return ["Нет конкретных действий"]
        return ["Проверить доступность указанных путей"]

    def reason(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run reasoning chain and return structured log."""
        chain: List[Step] = [Step("goal", goal), Step("context", context)]

        if context.get("unknown_host"):
            self.logger.debug(
                "Вижу неизвестный хост — возможно, стоит просканировать его через ping перед nmap."
            )

        hypotheses = self._generate_hypotheses(goal)
        chain.append(Step("hypotheses", hypotheses))

        plan = self._build_plan(hypotheses)
        chain.append(Step("plan", plan))

        actions: List[str] = []
        result: str = ""
        for path in hypotheses:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                actions.append(f"found {expanded}")
                result = f"found {expanded}"
                break
            else:
                actions.append(f"not found {expanded}")
        chain.append(Step("action", actions))

        if not result:
            result = "nothing found"
        chain.append(Step("evaluation", result))

        return {"chain": [asdict(s) for s in chain], "result": result}

    def decision_probability(
        self, context: Dict[str, Any], risk: float, goal: str, experience: float
    ) -> float:
        """Estimate probability of taking an action."""
        risk = max(0.0, min(risk, 1.0))
        exp_factor = max(0.0, min(experience, 1.0))
        ctx_factor = min(len(context) / 10.0, 1.0)
        goal_factor = 1.0 if goal else 0.5
        prob = (ctx_factor + exp_factor) * goal_factor * (1 - risk)
        return max(0.0, min(prob, 1.0))
