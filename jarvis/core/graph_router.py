"""
Graph-based command routing utilities.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from command_dispatcher import CommandDispatcher


@dataclass
class Node:
    """Represents a command execution step in the graph."""

    name: str
    command: str
    next: List[str] = field(default_factory=list)


class GraphRouter:
    """Loads and executes command graphs."""

    def __init__(self, dispatcher: CommandDispatcher) -> None:
        self.dispatcher = dispatcher
        self.nodes: Dict[str, Node] = {}
        self.path: Optional[str] = None

    @property
    def active(self) -> bool:
        return bool(self.nodes)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load_graph(self, path: str) -> None:
        """Load a graph definition from YAML or JSON."""
        file_path = Path(path)
        with open(file_path, "r", encoding="utf-8") as fh:
            if file_path.suffix in {".yaml", ".yml"}:
                data = yaml.safe_load(fh)
            elif file_path.suffix == ".json":
                data = json.load(fh)
            else:
                raise ValueError(f"Unsupported graph format: {file_path.suffix}")

        if not isinstance(data, dict):
            raise ValueError("Graph file must contain a mapping of nodes")

        nodes: Dict[str, Node] = {}
        for name, info in data.items():
            if not isinstance(info, dict) or "command" not in info:
                raise ValueError(f"Invalid node definition for {name}")
            nxt = info.get("next", [])
            if isinstance(nxt, str):
                nxt = [nxt]
            nodes[name] = Node(name=name, command=info["command"], next=list(nxt))

        self.nodes = nodes
        self.path = str(file_path)

    def reload_graph(self, path: Optional[str] = None) -> None:
        """Reload the current graph from disk."""
        target = path or self.path
        if not target:
            raise ValueError("No graph loaded")
        self.load_graph(target)

    def unload_graph(self) -> None:
        """Clear the active graph."""
        self.nodes.clear()
        self.path = None

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    async def execute(self, start_node: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute starting from ``start_node`` following ``next`` transitions."""
        if start_node not in self.nodes:
            raise ValueError(f"Unknown start node: {start_node}")
        context = context or {}
        return await self._execute_node(start_node, context, set())

    async def _execute_node(self, name: str, context: Dict[str, Any], seen: Set[str]) -> Dict[str, Any]:
        if name in seen:
            raise ValueError(f"Cycle detected at node {name}")
        node = self.nodes[name]
        seen.add(name)
        command = node.command.format(**context)
        result = await self.dispatcher.dispatch(command)
        results = {name: result}
        for nxt in node.next:
            if nxt not in self.nodes:
                raise ValueError(f"Unknown node: {nxt}")
            results.update(await self._execute_node(nxt, context, seen))
        seen.remove(name)
        return results
