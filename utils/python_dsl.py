import re
from typing import List, Dict

def parse_technical_description(text: str) -> Dict[str, List[str]]:
    """Extract simple bullet requirements from technical docs."""
    requirements = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(('-', '*', '•')) or line[0].isdigit():
            # remove leading numbering or bullets
            line = re.sub(r'^[-*•\d\.\)\s]+', '', line)
            requirements.append(line)
    return {"requirements": requirements}

def phrase_to_python(phrase: str) -> str:
    """Translate a short Russian phrase describing code into Python snippet."""
    pl = phrase.lower().strip()
    m = re.match(r"создай функцию ([a-zA-Z_][a-zA-Z0-9_]*)", pl)
    if m:
        name = m.group(1)
        return f"def {name}():\n    pass\n"
    m = re.match(r"создай класс ([a-zA-Z_][a-zA-Z0-9_]*)", pl)
    if m:
        cls = m.group(1).capitalize()
        return f"class {cls}:\n    pass\n"
    m = re.match(r"импортируй ([a-zA-Z0-9_\.]+)(?: как ([a-zA-Z_][a-zA-Z0-9_]*))?", pl)
    if m:
        mod, alias = m.group(1), m.group(2)
        if alias:
            return f"import {mod} as {alias}\n"
        return f"import {mod}\n"
    return "# Не удалось интерпретировать фразу"
