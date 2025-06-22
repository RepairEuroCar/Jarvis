from dataclasses import dataclass
import yaml
from pathlib import Path


@dataclass
class Task:
    id: str
    title: str
    description: str
    module: str
    action: str
    estimated_minutes: int

def load_tasks(path: str | Path = Path(__file__).with_name("tasks.yaml")) -> list[Task]:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or []
    return [Task(**item) for item in raw]
