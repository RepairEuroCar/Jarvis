"""Design helper for Jarvis projects."""

import re
from typing import dict, list


def design_module(task_description: str) -> dict[str, list[str] | str]:
    """Parse a natural language description and return a simple project design.

    The returned dictionary contains:
        - ``project_type``: detected high level type (e.g. ``telegram_bot``)
        - ``files``: list of relevant file names
        - ``classes``: list of class names to implement
    """
    text = task_description.lower()
    design: dict[str, list[str] | str] = {
        "project_type": "general",
        "files": [],
        "classes": [],
    }

    # Basic project type patterns
    patterns = {
        "telegram_bot": [["telegram", "bot"], ["телеграм", "бот"]],
        "web_app": [["web", "app"], ["веб", "приложение"]],
        "cli": [["cli"], ["команд", "стр"]],
        "scraper": [["scraper"], ["парсер"]],
    }
    for ptype, keyword_sets in patterns.items():
        if any(all(k in text for k in keywords) for keywords in keyword_sets):
            design["project_type"] = ptype
            if ptype == "telegram_bot":
                design["files"].extend(["bot.py", "config.py", "requirements.txt"])
                design["classes"].append("TelegramBot")
            elif ptype == "web_app":
                design["files"].extend(
                    ["app.py", "requirements.txt", "templates/index.html"]
                )
                design["classes"].append("WebApp")
            elif ptype == "cli":
                design["files"].extend(["cli.py", "requirements.txt"])
                design["classes"].append("CLI")
            elif ptype == "scraper":
                design["files"].extend(["scraper.py", "requirements.txt"])
                design["classes"].append("Scraper")
            break

    # Extract explicitly mentioned file names
    file_regex = re.compile(r"(?:file|файл|module)\s+([\w/]+\.py)", re.I)
    design["files"].extend(file_regex.findall(task_description))

    # Extract class names from text
    class_regex = re.compile(r"(?:class|класс)\s+([A-Z][A-Za-z0-9_]*)")
    design["classes"].extend(class_regex.findall(task_description))

    # Deduplicate and sort results
    design["files"] = sorted(set(design["files"]))
    design["classes"] = sorted(set(design["classes"]))

    return design
