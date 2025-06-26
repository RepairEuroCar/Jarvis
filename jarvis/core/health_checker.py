from __future__ import annotations

import aiohttp
from typing import Any, Dict, List

from utils.logger import get_logger

try:  # optional dependency
    import asyncpg  # type: ignore
except Exception:  # pragma: no cover - optional
    asyncpg = None

try:
    import aioredis  # type: ignore
except Exception:  # pragma: no cover - optional
    aioredis = None

logger = get_logger().getChild("HealthChecker")


class HealthChecker:
    """Check availability of external dependencies."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self.results: Dict[str, Any] = {}

    async def check_postgres(self) -> bool:
        dsn = getattr(self.settings, "db_dsn", None)
        if not dsn:
            return True
        if asyncpg is None:
            logger.warning("asyncpg not available for DB check")
            return False
        try:
            conn = await asyncpg.connect(dsn)
            await conn.execute("SELECT 1")
            await conn.close()
            return True
        except Exception as e:  # pragma: no cover - best effort
            logger.warning("PostgreSQL check failed: %s", e)
            return False

    async def check_redis(self) -> bool:
        url = getattr(self.settings, "redis_url", None)
        if not url:
            return True
        if aioredis is None:
            logger.warning("aioredis not available for Redis check")
            return False
        try:
            redis = aioredis.from_url(url)
            await redis.ping()
            await redis.close()
            return True
        except Exception as e:  # pragma: no cover - best effort
            logger.warning("Redis check failed: %s", e)
            return False

    async def check_ml_model(self, jarvis: Any) -> bool:
        try:
            model = getattr(jarvis.nlu, "intent_model", None)
            if model is None or not getattr(model, "_clf", None):
                return False
            model.predict("ping")
            return True
        except Exception as e:  # pragma: no cover - best effort
            logger.warning("ML model check failed: %s", e)
            return False

    async def check_external_apis(self) -> Dict[str, bool]:
        urls: List[str] = getattr(self.settings, "external_api_urls", [])
        if not urls:
            return {}
        results: Dict[str, bool] = {}
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.get(url) as resp:
                        results[url] = resp.status < 400
                except Exception as e:  # pragma: no cover - best effort
                    logger.warning("API %s check failed: %s", url, e)
                    results[url] = False
        return results

    async def run_all_checks(self, jarvis: Any) -> Dict[str, Any]:
        """Execute all dependency checks."""
        results = {
            "database": await self.check_postgres(),
            "redis": await self.check_redis(),
            "ml_model": await self.check_ml_model(jarvis),
            "external_apis": await self.check_external_apis(),
        }
        self.results = results
        return results
