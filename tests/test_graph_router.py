import json
import yaml
from command_dispatcher import CommandDispatcher
from jarvis.core.graph_router import GraphRouter

import pytest


@pytest.mark.asyncio
async def test_graph_loading_and_execution(tmp_path):
    graph = {
        "start": {"command": "util greet --name={name}", "next": "end"},
        "end": {"command": "util greet --name=bye"},
    }
    path = tmp_path / "g.yaml"
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(graph, fh)

    dispatcher = CommandDispatcher()

    def greet(name: str) -> str:
        return f"hello {name}"

    dispatcher.register_command_handler("util", "greet", greet)

    router = GraphRouter(dispatcher)
    router.load_graph(str(path))
    result = await router.execute("start", {"name": "John"})
    assert result["start"] == "hello John"
    assert result["end"] == "hello bye"


@pytest.mark.asyncio
async def test_graph_reload(tmp_path):
    path = tmp_path / "g.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"step": {"command": "util echo --text=1"}}, fh)

    dispatcher = CommandDispatcher()

    def echo(text: str) -> str:
        return text

    dispatcher.register_command_handler("util", "echo", echo)

    router = GraphRouter(dispatcher)
    router.load_graph(str(path))
    first = await router.execute("step")
    assert first["step"] == "1"

    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"step": {"command": "util echo --text=2"}}, fh)

    router.reload_graph()
    second = await router.execute("step")
    assert second["step"] == "2"
