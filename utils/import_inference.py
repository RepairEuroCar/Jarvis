"""Infer required imports from task descriptions."""

from typing import list

_HEURISTICS = {
    "telegram": ["import aiogram"],
    "телеграм": ["import aiogram"],
    "scrape": ["import requests", "from bs4 import BeautifulSoup"],
    "scraper": ["import requests", "from bs4 import BeautifulSoup"],
    "парсер": ["import requests", "from bs4 import BeautifulSoup"],
}


def infer_imports(description: str) -> list[str]:
    """Return a list of import statements inferred from ``description``."""
    text = description.lower()
    imports: list[str] = []
    for keyword, stmts in _HEURISTICS.items():
        if keyword in text:
            for stmt in stmts:
                if stmt not in imports:
                    imports.append(stmt)
    return imports


__all__ = ["infer_imports"]
