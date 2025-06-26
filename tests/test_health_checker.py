import importlib

import pytest
from fastapi.testclient import TestClient

from jarvis.core.main import Jarvis
from jarvis.core.health_checker import HealthChecker


@pytest.mark.asyncio
async def test_health_checker_runs(monkeypatch):
    jarvis = Jarvis()

    async def ok_db(self):
        return True

    async def ok_redis(self):
        return True

    async def ok_ml(self, j):
        return True

    async def ok_api(self):
        return {}

    monkeypatch.setattr(HealthChecker, "check_postgres", ok_db)
    monkeypatch.setattr(HealthChecker, "check_redis", ok_redis)
    monkeypatch.setattr(HealthChecker, "check_ml_model", ok_ml)
    monkeypatch.setattr(HealthChecker, "check_external_apis", ok_api)

    res = await jarvis.health_checker.run_all_checks(jarvis)
    assert res == {
        "database": True,
        "redis": True,
        "ml_model": True,
        "external_apis": {},
    }


def test_startup_healthcheck_endpoint(monkeypatch):
    async def fake_init(self):
        await self.health_checker.run_all_checks(self)

    async def fake_run(self, jarvis):
        self.results = {"database": True}
        return self.results

    monkeypatch.setattr(Jarvis, "initialize", fake_init)
    monkeypatch.setattr(HealthChecker, "run_all_checks", fake_run)

    import jarvis.rest_api as rest_api
    importlib.reload(rest_api)

    with TestClient(rest_api.app) as client:
        response = client.get("/startup/healthcheck")
        assert response.status_code == 200
        assert response.json() == {"database": True}
