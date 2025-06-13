import pytest

from command_dispatcher import CommandDispatcher


@pytest.mark.asyncio
async def test_dispatch_sync_handler():
    dispatcher = CommandDispatcher()

    def greet(name: str) -> str:
        return f"hello {name}"

    dispatcher.register_command_handler("util", "greet", greet)

    result = await dispatcher.dispatch("util greet --name=Jarvis")
    assert result == "hello Jarvis"


@pytest.mark.asyncio
async def test_dispatch_async_handler():
    dispatcher = CommandDispatcher()

    async def add(x: str, y: str) -> int:
        return int(x) + int(y)

    dispatcher.register_command_handler("calc", "add", add)

    result = await dispatcher.dispatch("calc add --x=1 --y=2")
    assert result == 3


@pytest.mark.asyncio
async def test_unknown_command():
    dispatcher = CommandDispatcher()
    result = await dispatcher.dispatch("unknown cmd")
    assert result is None


@pytest.mark.asyncio
async def test_dynamic_module_registration():
    dispatcher = CommandDispatcher()

    def foo() -> str:
        return "bar"

    dispatcher.register_command_handler("newmod", "foo", foo)

    result = await dispatcher.dispatch("newmod foo")
    assert result == "bar"

    commands = await dispatcher.dispatch("list_commands")
    assert "newmod foo" in commands.splitlines()
