import asyncio
import logging
import shlex
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional


class CommandDispatcher:
    """Simple command dispatcher parsing ``module action --param=value`` input."""

    EXIT = object()

    def __init__(self, jarvis: Optional[Any] = None) -> None:
        self.jarvis = jarvis
        self.logger = logging.getLogger("CommandDispatcher")
        self._handlers: Dict[str, Dict[Optional[str], Callable[..., Any]]] = {}
        self._register_builtin_commands()

    # ------------------------------------------------------------------
    # Registration utilities
    # ------------------------------------------------------------------
    def register_command_handler(
        self, module: str, action: Optional[str], handler: Callable[..., Any]
    ) -> None:
        """Register a handler for ``module action``."""
        self._handlers.setdefault(module, {})[action] = handler

    def command(self, module: str, action: Optional[str]):
        """Decorator for registering command handlers."""

        def decorator(func: Callable[..., Any]):
            self.register_command_handler(module, action, func)
            return func

        return decorator

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def parse(self, text: str) -> Optional[tuple[str, Optional[str], Dict[str, str]]]:
        """Parse ``text`` into module, action and ``--key=value`` pairs."""
        tokens = shlex.split(text)
        if not tokens:
            return None
        module = tokens[0]
        action: Optional[str] = None
        params_tokens = tokens[1:]
        if params_tokens and not params_tokens[0].startswith("--"):
            action = params_tokens[0]
            params_tokens = params_tokens[1:]
        params: Dict[str, str] = {}
        for token in params_tokens:
            if token.startswith("--") and "=" in token:
                key, val = token[2:].split("=", 1)
                params[key] = val
        return module, action, params

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    async def dispatch(self, text: str) -> Any:
        parsed = self.parse(text)
        if not parsed:
            return None
        module, action, params = parsed
        handler = self._handlers.get(module, {}).get(action)
        if not handler:
            return None
        self.logger.info("Invoking %s %s with %s", module, action, params)
        if asyncio.iscoroutinefunction(handler):
            return await handler(**params)
        return handler(**params)

    # ------------------------------------------------------------------
    # Built-in commands
    # ------------------------------------------------------------------
    def _register_builtin_commands(self) -> None:
        self.register_command_handler("help", None, self._help)
        self.register_command_handler("exit", None, self._exit)
        self.register_command_handler("list_commands", None, self._list_commands)
        self.register_command_handler("reload", None, self._reload)

    def _list_commands(self, **_: str) -> str:
        lines = []
        for mod, actions in self._handlers.items():
            for act in actions:
                if mod in {"help", "exit", "list_commands", "reload"} and act is None:
                    lines.append(mod)
                else:
                    lines.append(f"{mod} {act}")
        return "\n".join(sorted(lines))

    def _help(self, command: str | None = None, **_: str) -> str:
        if not command:
            return (
                "Enter <module> <action> [--param=value]..."
                "\nAvailable commands:\n" + self._list_commands()
            )
        tokens = command.split()
        module = tokens[0]
        action = tokens[1] if len(tokens) > 1 else None
        handler = self._handlers.get(module, {}).get(action)
        if not handler:
            return "Command not found"
        doc = handler.__doc__ or "No description"
        return doc.strip()

    def _exit(self, **_: str) -> Any:
        return self.EXIT

    async def _reload(self, module: str | None = None, **_: str) -> str:
        if not module:
            return "Usage: reload --module=<name>"
        if not self.jarvis or not hasattr(self.jarvis, "module_manager"):
            return "Reload not supported"
        success = await self.jarvis.module_manager.reload_module(module)
        return f"Module {module} reloaded" if success else f"Failed to reload {module}"
