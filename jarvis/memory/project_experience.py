import time
from dataclasses import asdict, dataclass, field
from typing import Any

from jarvis.memory.manager import MemoryManager


@dataclass
class ProjectExperience:
    """Record of a single project related task."""

    task: str
    code_refs: list[str] = field(default_factory=list)
    outcome: str = ""
    tags: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ProjectExperience":
        return ProjectExperience(
            task=data.get("task", ""),
            code_refs=list(data.get("code_refs", [])),
            outcome=data.get("outcome", ""),
            tags=list(data.get("tags", [])),
            timestamp=float(data.get("timestamp", time.time())),
        )


def _load_raw(memory: MemoryManager) -> list[dict[str, Any]]:
    stored = memory.recall("projects.experience")
    return stored if isinstance(stored, list) else []


def load_experiences(memory: MemoryManager) -> list[ProjectExperience]:
    """Load all project experiences from memory."""
    return [ProjectExperience.from_dict(e) for e in _load_raw(memory)]


async def save_experience(memory: MemoryManager, exp: ProjectExperience) -> None:
    """Persist a new project experience to memory."""
    data = _load_raw(memory)
    data.append(exp.to_dict())
    await memory.remember("projects.experience", data, category="project")


def query_experiences(
    memory: MemoryManager,
    tags : None | [list[str]] = None,
    text : None | [str] = None,
) -> list[ProjectExperience]:
    """Return experiences matching ``tags`` and/or ``text``."""
    tags_set = set(t.lower() for t in tags) if tags else None
    text_l = text.lower() if text else None
    results: list[ProjectExperience] = []
    for exp in load_experiences(memory):
        if tags_set and not tags_set.intersection({t.lower() for t in exp.tags}):
            continue
        if text_l and text_l not in exp.task.lower():
            continue
        results.append(exp)
    return results
