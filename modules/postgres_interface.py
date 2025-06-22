"""PostgreSQL integration for Jarvis users.

This optional module sets up the improved `jarvis_users` schema and exposes a
simple command to list users. It relies on `asyncpg` for connection pooling.
"""

from pathlib import Path
from typing import Any

import asyncpg

DATABASE_DSN = "postgresql://localhost/jarvis"
SCHEMA_FILES = [
    Path("docs/jarvis_users_pg.sql"),
    Path("docs/jarvis_topics_pg.sql"),
]


async def load_module(jarvis_instance: Any, dsn: str = DATABASE_DSN) -> None:
    """Initialise a connection pool and ensure the schema exists."""

    jarvis_instance.pg_pool = await asyncpg.create_pool(dsn)
    for path in SCHEMA_FILES:
        if path.exists():
            sql = path.read_text()
            async with jarvis_instance.pg_pool.acquire() as conn:
                await conn.execute(sql)

    jarvis_instance.commands["list_pg_users"] = list_users_async


async def close_module(jarvis_instance: Any) -> None:
    """Close the connection pool when the module is unloaded."""

    pool = getattr(jarvis_instance, "pg_pool", None)
    if pool:
        await pool.close()
        jarvis_instance.pg_pool = None


async def list_users_async(jarvis_instance: Any, _: str = "") -> str:
    """Return a list of registered users."""

    pool = getattr(jarvis_instance, "pg_pool", None)
    if not pool:
        return "PostgreSQL module is not loaded"

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT username, security_level FROM jarvis_users ORDER BY username"
        )
    if not rows:
        return "No users found."
    return "\n".join(f"{r['username']} (level {r['security_level']})" for r in rows)


commands = {"list_pg_users": list_users_async}
