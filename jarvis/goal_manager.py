from __future__ import annotations

import time
from typing import Any, Dict, Optional


class GoalManager:
    """Simple manager for storing a current goal with motivation."""

    def __init__(self, jarvis: Any) -> None:
        self.jarvis = jarvis

    def set_goal(self, goal: str, motivation: str = "") -> None:
        """Store a goal and motivation in Jarvis memory."""
        data = {
            "goal": goal,
            "motivation": motivation,
            "timestamp": time.time(),
        }
        self.jarvis.memory.remember("goals.current", data, category="goals")
        history = self.jarvis.memory.recall("goals.history") or []
        history.append(data)
        self.jarvis.memory.remember("goals.history", history, category="goals")

    def get_goal(self) -> Optional[Dict[str, Any]]:
        """Return the currently stored goal information."""
        return self.jarvis.memory.recall("goals.current")

    def clear_goal(self) -> None:
        """Remove the current goal from memory."""
        self.jarvis.memory.forget("goals.current")
