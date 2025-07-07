import asyncio
import inspect
import shlex
from dataclasses import dataclass
from typing import Any, Callable, Tuple, Type, Union

from loguru import logger
from pydantic import BaseModel, ValidationError, ConfigDict

# Custom types
CommandResult = Union[Any, None]
CommandHandler = Callable[..., CommandResult]
ParamModel = Type[BaseModel]


@dataclass
class CommandContext:
    """Context object passed to command handlers"""

    user: str
    timestamp: float
    raw_input: str
    is_async: bool


class CommandError(Exception):
    """Base error for all command-related exceptions."""

    def __init__(self, message: str, command: str | None = None) -> None:
        self.message = message
        self.command = command
        super().__init__(message)


class InvalidCommandError(CommandError):
    """Raised when command parsing fails"""


class CommandExecutionError(CommandError):
    """Raised when command execution fails"""


class CommandDispatcher:
    """Advanced command dispatcher with async support and parameter validation.

    Features:
    - Async/sync command handlers
    - Pydantic parameter validation
    - Context injection
    - Comprehensive error handling
    - Command chaining
    - Middleware support
    """

    EXIT = object()
    _middlewares: list[Callable] = []
    class _ModuleModel(BaseModel):
        module: str
        model_config = ConfigDict(extra="forbid")

    class _NoParamsModel(BaseModel):
        model_config = ConfigDict(extra="forbid")

    def __init__(
        self, jarvis: Any | None = None, prefix: str = "", timeout: float = 30.0
    ) -> None:
        self.jarvis = jarvis
        self._handlers: dict[str, dict[str | None, CommandHandler]] = {}
        self._param_models: dict[str, dict[str | None, ParamModel]] = {}
        self.prefix = prefix
        self.timeout = timeout
        self._register_builtins()

    def register_middleware(self, middleware: Callable):
        """Register preprocessing middleware"""
        self._middlewares.append(middleware)
        return middleware

    def command(
        self,
        module: str,
        action: str | None = None,
        *,
        param_model: ParamModel | None = None,
    ):
        """Decorator for registering command handlers."""

        def decorator(func: CommandHandler):
            self.register(
                module=module, action=action, handler=func, param_model=param_model
            )
            return func

        return decorator

    def register(
        self,
        module: str,
        handler: CommandHandler,
        action: str | None = None,
        param_model: ParamModel | None = None,
    ):
        """Register a command handler."""
        if module not in self._handlers:
            self._handlers[module] = {}
            self._param_models[module] = {}

        self._handlers[module][action] = handler

        if param_model:
            self._param_models[module][action] = param_model
        elif action in self._param_models.get(module, {}):
            del self._param_models[module][action]

    # ------------------------------------------------------------------
    # Compatibility helpers used by tests and modules
    def register_command_handler(
        self,
        module: str,
        action: str | None,
        handler: CommandHandler,
        param_model: ParamModel | None = None,
    ) -> None:
        self.register(module=module, action=action, handler=handler, param_model=param_model)

    def parse(self, text: str) -> Tuple[str, str | None, dict[str, str]]:
        return self._parse_command(text)

    async def dispatch(
        self, text: str, context: dict | None = None
    ) -> CommandResult:
        """Execute a command with full error handling.

        Args:
            text: Command string to execute
            context: Additional execution context

        Returns:
            Command execution result or None if command not found

        Raises:
            InvalidCommandError: For parsing/validation errors
            CommandExecutionError: For execution errors
        """
        # Apply middleware preprocessing
        for middleware in self._middlewares:
            text = await self._run_middleware(middleware, text)

        try:
            module, action, params = self._parse_command(text)
            handler = self._get_handler(module, action)

            if handler is None:
                logger.debug(f"Command not found: {module} {action or ''}")
                return None

            ctx = self._create_context(text, handler)
            validated_params = self._validate_params(module, action, params)

            return await self._execute_handler(
                handler=handler,
                params=validated_params,
                context={**(context or {}), **ctx},
            )

        except InvalidCommandError:
            raise
        except Exception as e:
            logger.error(f"Command failed: {text}", exc_info=True)
            raise CommandExecutionError(f"Command execution failed: {e}", text) from e

    async def dispatch_chain(self, commands: list[str]) -> list[CommandResult]:
        """Execute multiple commands sequentially."""
        results = []
        for cmd in commands:
            try:
                result = await self.dispatch(cmd)
                results.append(result)
                if result is self.EXIT:
                    break
            except CommandError as e:
                results.append(e)
        return results

    def _parse_command(self, text: str) -> Tuple[str, str | None, dict[str, str]]:
        """Parse command string into components."""
        try:
            tokens = shlex.split(text[len(self.prefix) :] if self.prefix else text)
            if not tokens:
                raise InvalidCommandError("Empty command")

            module = tokens[0]
            action = (
                tokens[1] if len(tokens) > 1 and not tokens[1].startswith("-") else None
            )
            params = self._parse_params(tokens[2:] if action else tokens[1:])

            return module, action, params
        except ValueError as e:
            raise InvalidCommandError(f"Invalid command syntax: {e}") from e

    def _parse_params(self, tokens: list[str]) -> dict[str, str]:
        """Parse command parameters from tokens."""
        params = {}
        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.startswith("--"):
                # Long option (--key=value or --flag)
                if "=" in token:
                    key, val = token[2:].split("=", 1)
                    params[key] = val
                else:
                    params[token[2:]] = "true"
            elif token.startswith("-") and len(token) > 1:
                # Short option (-k value or -v)
                key = token[1:]
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                    params[key] = tokens[i + 1]
                    i += 1
                else:
                    params[key] = "true"
            else:
                raise InvalidCommandError(f"Invalid parameter: {token}")

            i += 1

        return params

    def _get_handler(
        self, module: str, action: str | None
    ) -> CommandHandler | None:
        """Get handler for command if exists."""
        return self._handlers.get(module, {}).get(action)

    def _validate_params(
        self, module: str, action: str | None, params: dict[str, str]
    ) -> dict[str, Any]:
        """Validate parameters against model if available."""
        model = self._param_models.get(module, {}).get(action)
        if not model:
            return params

        try:
            return model(**params).dict()
        except ValidationError as e:
            raise InvalidCommandError(f"Invalid parameters: {e}") from e

    def _create_context(self, text: str, handler: CommandHandler) -> dict[str, Any]:
        """Create execution context."""
        return {
            "raw_input": text,
            "is_async": asyncio.iscoroutinefunction(handler),
            "timestamp": asyncio.get_event_loop().time(),
        }

    async def _execute_handler(
        self, handler: CommandHandler, params: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        """Execute handler with timeout and context injection."""
        # Inject context if handler accepts it
        if "context" in inspect.signature(handler).parameters:
            params["context"] = context

        try:
            if asyncio.iscoroutinefunction(handler):
                return await asyncio.wait_for(handler(**params), timeout=self.timeout)
            return handler(**params)
        except asyncio.TimeoutError:
            raise CommandExecutionError("Command timed out")
        except Exception:
            logger.opt(exception=True).error("Handler execution failed")
            raise

    async def _run_middleware(self, middleware: Callable, text: str) -> str:
        """Run middleware with proper async/sync handling."""
        if asyncio.iscoroutinefunction(middleware):
            return await middleware(text)
        return middleware(text)

    def _register_builtins(self):
        """Register built-in commands."""
        self.register("help", self._help, param_model=self._NoParamsModel)
        self.register("exit", lambda: self.EXIT, param_model=self._NoParamsModel)
        self.register("list_commands", self._list_commands, param_model=self._NoParamsModel)
        self.register("load", self._load_module, param_model=self._ModuleModel)
        self.register("unload", self._unload_module, param_model=self._ModuleModel)
        self.register("reload", self._reload_module, param_model=self._ModuleModel)

    async def _load_module(self, module: str) -> str:
        if not (self.jarvis and getattr(self.jarvis, "module_manager", None)):
            return "Load not supported"
        success = await self.jarvis.module_manager.load_module(module)
        return f"Module {module} loaded" if success else f"Failed to load module {module}"

    async def _unload_module(self, module: str) -> str:
        if not (self.jarvis and getattr(self.jarvis, "module_manager", None)):
            return "Unload not supported"
        success = await self.jarvis.module_manager.unload_module(module)
        return f"Module {module} unloaded" if success else f"Failed to unload module {module}"

    async def _reload_module(self, module: str) -> str:
        if not (self.jarvis and getattr(self.jarvis, "module_manager", None)):
            return "Reload not supported"
        success = await self.jarvis.module_manager.reload_module(module)
        return f"Module {module} reloaded" if success else f"Failed to reload module {module}"

    async def _help(self, command: str | None = None) -> str:
        """Show help for commands."""
        if command:
            handler = next(
                (
                    h
                    for mod in self._handlers.values()
                    for act, h in mod.items()
                    if f"{act if act else ''}" == command
                ),
                None,
            )
            if not handler:
                return f"No help available for: {command}"
            return inspect.getdoc(handler) or "No documentation available"

        return "\n".join(
            f"{mod} {act if act else ''}"
            for mod in self._handlers
            for act in self._handlers[mod]
        )

    def _list_commands(self) -> str:
        """List all registered commands."""
        cmds = [
            f"{self.prefix}{mod} {act if act else ''}".rstrip()
            for mod in self._handlers
            for act in self._handlers[mod]
        ]
        return "\n".join(cmds)


# Global dispatcher instance
default_dispatcher = CommandDispatcher()
