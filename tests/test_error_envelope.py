import pytest
from httpx import AsyncClient

from tests.conftest import seed_and_login


@pytest.mark.anyio
async def test_unauthenticated_requests_have_a_code(client: AsyncClient) -> None:
    response = await client.get("/api/v1/scheduling/review-queue")

    assert response.status_code == 401
    assert response.json() == {"detail": "missing session", "code": "unauthenticated"}


@pytest.mark.anyio
async def test_not_found_and_conflict_carry_codes(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")

    missing = await client.get("/api/v1/scheduling/schedule-periods/sp_missing")
    duplicate = await client.post("/api/v1/scheduling/departments", json={"name": "Emergency", "code": "ER"})

    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "department code already exists", "code": "conflict"}


@pytest.mark.anyio
async def test_validation_errors_list_the_offending_fields(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")

    response = await client.post("/api/v1/scheduling/departments", json={"name": "X", "code": ""})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert {item["field"] for item in body["fields"]} == {"name", "code"}
    assert body["detail"].startswith("Validation failed:")


@pytest.mark.anyio
async def test_health_reports_version_and_demo_mode(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["demo_mode"] is True
    assert body["version"] == open("VERSION").read().strip()
