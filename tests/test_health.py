from fastapi.testclient import TestClient

from apps.api.app.main import app


client = TestClient(app)


def test_healthcheck() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scheduling_capabilities() -> None:
    response = client.get("/api/v1/scheduling/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["phase"] == "phase-1-core"
    assert "rules" in body["modules"]

