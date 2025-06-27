from fastapi.testclient import TestClient
import jarvis.rest_api as rest_api


async def dummy_init():
    return None


async def dummy_health():
    return {"alpha": True, "beta": False}


def test_selfcheck_endpoint(monkeypatch):
    monkeypatch.setattr(rest_api.jarvis, "initialize", dummy_init)
    monkeypatch.setattr(rest_api.jarvis.module_manager, "health_check_all", dummy_health)

    with TestClient(rest_api.app) as client:
        response = client.get("/selfcheck")
        assert response.status_code == 200
        data = response.json()
        assert data["modules"] == {"alpha": True, "beta": False}
        assert set(data["modules"].keys()) == {"alpha", "beta"}
