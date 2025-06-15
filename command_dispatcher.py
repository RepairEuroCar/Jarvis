import asyncio
import logging
import shlex
from typing import Any, Callable, Dict, Optional, Type

from pydantic import BaseModel, ValidationError


class HelpParams(BaseModel):
    command: Optional[str] = None

    class Config:
        extra = "forbid"


class ExitParams(BaseModel):
    class Config:
        extra = "forbid"


class ListCommandsParams(BaseModel):
    class Config:
        extra = "forbid"


class ReloadParams(BaseModel):
    module: Optional[str] = None

    class Config:
        extra = "forbid"


class CommandError(Exception):
    """Base error raised by :class:`CommandDispatcher`."""


class InvalidCommandError(CommandError):
    """Raised when the input command cannot be parsed."""


class CommandDispatcher:
    """Simple command dispatcher parsing ``module action --param=value`` style
    commands.

    Parameters can be provided as ``--key=value``, ``--flag`` for booleans or
    short options like ``-k value`` and ``-v``.
    """

    EXIT = object()

    def __init__(self, jarvis: Optional[Any] = None) -> None:
        self.jarvis = jarvis
        self.logger = logging.getLogger("CommandDispatcher")
        self._handlers: Dict[str, Dict[Optional[str], Callable[..., Any]]] = {}
        self._param_models: Dict[str, Dict[Optional[str], Type[BaseModel]]] = {}
        self._register_builtin_commands()

    # ------------------------------------------------------------------
    # Registration utilities
    # ------------------------------------------------------------------
    def register_command_handler(
        self,
        module: str,
        action: Optional[str],
        handler: Callable[..., Any],
        param_model: Type[BaseModel] | None = None,
    ) -> None:
        """Register a handler for ``module action``."""
        self._handlers.setdefault(module, {})[action] = handler
        if param_model:
            self._param_models.setdefault(module, {})[action] = param_model

    def command(
        self,
        module: str,
        action: Optional[str],
        param_model: Type[BaseModel] | None = None,
    ):
        """Decorator for registering command handlers."""

        def decorator(func: Callable[..., Any]):
            self.register_command_handler(module, action, func, param_model)
            return func

        return decorator

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def parse(self, text: str) -> tuple[str, Optional[str], Dict[str, str]]:
        """Parse ``text`` into module, action and parameter key/value pairs.

        Supported parameter syntaxes are::

            --key=value  # key/value pair
            --flag       # boolean flag ("true")
            -k value     # short option with separate value
            -v           # short boolean flag
        """
        try:
            tokens = shlex.split(text)
        except ValueError as exc:  # unmatched quotes etc
            raise InvalidCommandError(str(exc)) from exc

        if not tokens:
            raise InvalidCommandError("No command provided")

        module = tokens[0]
        action: Optional[str] = None
        idx = 1
        if idx < len(tokens) and not tokens[idx].startswith("-"):
            action = tokens[idx]
            idx += 1

        params: Dict[str, str] = {}
        while idx < len(tokens):
            token = tokens[idx]
            if token.startswith("--"):
                if "=" in token:
                    key, val = token[2:].split("=", 1)
                    if not key:
                        raise InvalidCommandError(f"Malformed parameter: {token}")
                    params[key] = val
                else:
                    key = token[2:]
                    if not key:
                        raise InvalidCommandError(f"Malformed parameter: {token}")
                    params[key] = "true"
            elif token.startswith("-") and len(token) > 1:
                key = token[1:]
                if not key:
                    raise InvalidCommandError(f"Malformed parameter: {token}")
                if idx + 1 < len(tokens) and not tokens[idx + 1].startswith("-"):
                    idx += 1
                    params[key] = tokens[idx]
                else:
                    params[key] = "true"
            else:
                raise InvalidCommandError(f"Malformed parameter: {token}")
            idx += 1

        return module, action, params

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    async def dispatch(self, text: str) -> Any:
        module, action, params = self.parse(text)
        handler = self._handlers.get(module, {}).get(action)
        if not handler:
            return None
        model = self._param_models.get(module, {}).get(action)
        if model:
            try:
                params = model(**params).dict()
            except ValidationError as exc:
                raise InvalidCommandError(str(exc)) from exc
        self.logger.info("Invoking %s %s with %s", module, action, params)
        if asyncio.iscoroutinefunction(handler):
            return await handler(**params)
        return handler(**params)

    # ------------------------------------------------------------------
    # Built-in commands
    # ------------------------------------------------------------------
    def _register_builtin_commands(self) -> None:
        self.register_command_handler("help", None, self._help, HelpParams)
        self.register_command_handler("exit", None, self._exit, ExitParams)
        self.register_command_handler(
            "list_commands", None, self._list_commands, ListCommandsParams
        )
        self.register_command_handler("reload", None, self._reload, ReloadParams)

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
                "Enter <module> <action> [--param=value|--flag|-k value]..."
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


# Global dispatcher used for modules that register handlers on import
default_dispatcher = CommandDispatcher()
