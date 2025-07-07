from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(order=True)
class Goal:
    """Representation of a single goal."""

    priority: int
    goal: str = field(compare=False)
    motivation: str = field(default="", compare=False)
    deadline: float | None = field(default=None, compare=False)
    source: str = field(default="user", compare=False)
    timestamp: float = field(default_factory=time.time, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GoalManager:
    """Manage multiple goals with priority."""

    def __init__(self, jarvis: Any) -> None:
        self.jarvis = jarvis
        self._active_goals: list[Goal] = []
        stored = self.jarvis.memory.recall("goals.active") or []
        for g in stored:
            self._active_goals.append(Goal(**g))
        self._active_goals.sort(reverse=True)

    # ------------------------------------------------------------------
    # Compatibility helpers
    async def set_goal(self, goal: str, motivation: str = "") -> None:
        """Set a single goal (compatibility wrapper)."""
        self._active_goals.clear()
        await self.add_goal(goal, motivation)
        await self.jarvis.memory.remember(
            "goals.current", self._active_goals[0].to_dict(), category="goals"
        )

    def get_goal(self) -> dict[str, Any] | None:
        """Return the highest priority goal if available."""
        if not self._active_goals:
            return None
        return self._active_goals[0].to_dict()

    async def clear_goal(self) -> None:
        """Remove all active goals."""
        self._active_goals.clear()
        await self.jarvis.memory.forget("goals.current")
        await self.jarvis.memory.remember("goals.active", [], category="goals")

    # ------------------------------------------------------------------
    async def add_goal(
        self,
        goal: str,
        motivation: str = "",
        priority: int = 1,
        deadline: float | None = None,
        source: str = "user",
    ) -> Goal:
        """Add a goal to the active list."""

        new_goal = Goal(
            priority=priority,
            goal=goal,
            motivation=motivation,
            deadline=deadline,
            source=source,
        )
        self._active_goals.append(new_goal)
        self._active_goals.sort(reverse=True)
        await self.jarvis.memory.remember(
            "goals.active", [g.to_dict() for g in self._active_goals], category="goals"
        )
        history = self.jarvis.memory.recall("goals.history") or []
        history.append(new_goal.to_dict())
        await self.jarvis.memory.remember("goals.history", history, category="goals")
        return new_goal

    def list_goals(self) -> list[dict[str, Any]]:
        """Return active goals ordered by priority."""

        return [g.to_dict() for g in self._active_goals]

    async def remove_goal(self, index: int) -> bool:
        """Remove a goal by index."""

        if index < 0 or index >= len(self._active_goals):
            return False
        del self._active_goals[index]
        await self.jarvis.memory.remember(
            "goals.active", [g.to_dict() for g in self._active_goals], category="goals"
        )
        if self._active_goals:
            await self.jarvis.memory.remember(
                "goals.current", self._active_goals[0].to_dict(), category="goals"
            )
        else:
            await self.jarvis.memory.forget("goals.current")
        return True
