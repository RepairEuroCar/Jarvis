"""PostgreSQL integration for Jarvis users."""

import logging
from pathlib import Path
from typing import Any

REQUIRES = ["asyncpg"]

import asyncpg

logger = logging.getLogger(__name__)

DATABASE_DSN = "postgresql://localhost/jarvis"
SCHEMA_FILES = [
    Path("docs/jarvis_users_pg.sql"),
    Path("docs/jarvis_topics_pg.sql"),
]


async def load_module(jarvis_instance: Any, dsn: str = DATABASE_DSN) -> None:
    """Initialize connection pool and ensure schema exists."""
    jarvis_instance.pg_pool = await asyncpg.create_pool(dsn)
    
    for path in SCHEMA_FILES:
        if path.exists():
            sql = path.read_text()
            async with jarvis_instance.pg_pool.acquire() as conn:
                await conn.execute(sql)

    jarvis_instance.commands["list_pg_users"] = list_users_async


async def close_module(jarvis_instance: Any) -> None:
    """Close the connection pool when module is unloaded."""
    pool = getattr(jarvis_instance, "pg_pool", None)
    if pool:
        await pool.close()
        jarvis_instance.pg_pool = None


async def list_users_async(
    jarvis_instance: Any, 
    _: str = ""
) -> str:
    """Return a list of registered users."""
    pool = getattr(jarvis_instance, "pg_pool", None)
    if not pool:
        return "PostgreSQL module is not loaded"

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT username, security_level FROM jarvis_users "
            "ORDER BY username"
        )
    
    if not rows:
        return "No users found."
    
    return "\n".join(
        f"{r['username']} (level {r['security_level']})" for r in rows
    )


commands = {"list_pg_users": list_users_async}


async def health_check() -> bool:
    """Check that asyncpg is importable and DSN parsable."""
    try:
        _ = asyncpg.Connection
        return True
    except Exception as exc:
        logger.warning("Postgres interface health check failed: %s", exc)
        return False