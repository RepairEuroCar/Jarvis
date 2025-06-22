import pytest

from command_dispatcher import CommandDispatcher, InvalidCommandError


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


def test_parse_invalid_command():
    dispatcher = CommandDispatcher()
    with pytest.raises(InvalidCommandError):
        dispatcher.parse("")
    with pytest.raises(InvalidCommandError):
        dispatcher.parse("foo bar --=oops")


def test_parse_flags_and_short_options():
    dispatcher = CommandDispatcher()
    module, action, params = dispatcher.parse(
        "foo bar --flag -v -k value --name=Jarvis"
    )
    assert module == "foo"
    assert action == "bar"
    assert params["flag"] == "true"
    assert params["v"] == "true"
    assert params["k"] == "value"
    assert params["name"] == "Jarvis"


@pytest.mark.asyncio
async def test_builtin_param_validation():
    dispatcher = CommandDispatcher()

    with pytest.raises(InvalidCommandError):
        await dispatcher.dispatch("list_commands --extra=1")

    with pytest.raises(InvalidCommandError):
        await dispatcher.dispatch("help --bad=1")

    with pytest.raises(InvalidCommandError):
        await dispatcher.dispatch("exit --now=1")

    with pytest.raises(InvalidCommandError):
        await dispatcher.dispatch("reload --module=x --foo=bar")

    result = await dispatcher.dispatch("reload --module=test")
    assert "not supported" in result.lower()


@pytest.mark.asyncio
async def test_dispatch_chain():
    dispatcher = CommandDispatcher()

    calls: list[str] = []

    def first() -> str:
        calls.append("a")
        return "first"

    def second() -> str:
        calls.append("b")
        return "second"

    dispatcher.register_command_handler("mod", "a", first)
    dispatcher.register_command_handler("mod", "b", second)

    results = await dispatcher.dispatch_chain(["mod a", "mod b"])
    assert results == ["first", "second"]
    assert calls == ["a", "b"]
