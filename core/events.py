import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

_emitter: Callable[[str, Any], None] | None = None


def register_event_emitter(emitter: Callable[[str, Any], None]) -> None:
    """Register a callable used to emit events."""
    global _emitter
    _emitter = emitter


def emit_event(event_name: str, data: Any) -> None:
    if _emitter:
        try:
            _emitter(event_name, data)
        except Exception:  # pragma: no cover - best effort logging
            logger.exception("Event emitter failed for %s", event_name)
    else:
        logger.info("Event %s: %s", event_name, data)
