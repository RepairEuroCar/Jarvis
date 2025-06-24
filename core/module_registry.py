from typing import Callable, List, Any

_supplier: Callable[[], List[Any]] | None = None


def register_module_supplier(func: Callable[[], List[Any]]) -> None:
    global _supplier
    _supplier = func


def get_active_modules() -> List[Any]:
    if _supplier:
        return _supplier()
    return []
