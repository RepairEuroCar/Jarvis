from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Task:
    id: str
    title: str
    description: str
    module: str
    action: str
    estimated_minutes: int


def load_tasks(path: str | Path = Path(__file__).with_name("tasks.yaml")) -> list[Task]:
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or []
    return [Task(**item) for item in raw]
