from typing import Any, Callable

_supplier: Callable[[], list[Any]] | None = None


def register_module_supplier(func: Callable[[], list[Any]]) -> None:
    global _supplier
    _supplier = func


def get_active_modules() -> list[Any]:
    if _supplier:
        return _supplier()
    return []
