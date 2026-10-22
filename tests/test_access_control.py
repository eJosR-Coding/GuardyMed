import pytest
from httpx import AsyncClient

from tests.conftest import build_manager_flow, login, login_as_scoped_manager, seed_and_login

BASE = "/api/v1/scheduling"


async def _demo_department_id(client: AsyncClient) -> str:
    departments = await client.get(f"{BASE}/departments")
    return next(item["id"] for item in departments.json() if item["code"] == "ER")


@pytest.mark.anyio
async def test_scoped_manager_cannot_touch_another_departments_schedule(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    er_id = await _demo_department_id(client)
    ids = await build_manager_flow(client)  # creates a second department (PED) with a period

    await login_as_scoped_manager(client, department_id=er_id)

    assert (await client.get(f"{BASE}/schedule-periods/{ids['period_id']}")).status_code == 403
    assert (await client.get(f"{BASE}/schedule-periods/{ids['period_id']}/calendar")).status_code == 403
    assert (
        await client.patch(f"{BASE}/schedule-periods/{ids['period_id']}", json={"status": "in_review"})
    ).status_code == 403
    assert (
        await client.post(
            f"{BASE}/schedule-periods/{ids['period_id']}/assignments",
            json={
                "worker_id": ids["worker_id"],
                "assignment_type": "on_call",
                "shift_date": "2026-09-10",
                "start_time": "08:00:00",
                "end_time": "10:00:00",
            },
        )
    ).status_code == 403

    periods = await client.get(f"{BASE}/schedule-periods")
    assert periods.status_code == 200
    assert all(item["department_id"] == er_id for item in periods.json()["items"])
    departments = await client.get(f"{BASE}/departments")
    assert [item["id"] for item in departments.json()] == [er_id]
    workers = await client.get(f"{BASE}/workers")
    assert all(item["department_id"] == er_id for item in workers.json())


@pytest.mark.anyio
async def test_scoped_manager_queues_exclude_other_departments(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    er_id = await _demo_department_id(client)
    ids = await build_manager_flow(client)
    # A pending change request in the second department, created by that department's worker.
    from apps.api.app.api.auth import UserRole, create_user

    create_user(
        email="ped.worker@guardymed.local",
        full_name="Carla Mendez",
        password="password123",
        role=UserRole.WORKER,
        worker_id=ids["worker_id"],
        department_id=ids["department_id"],
    )
    await client.post("/api/v1/auth/logout")
    await login(client, "ped.worker@guardymed.local")
    created = await client.post(
        f"{BASE}/assignments/{ids['assignment_id']}/change-requests",
        json={"request_type": "adjustment", "reason": "Dentist appointment"},
    )
    assert created.status_code == 201, created.text

    await login_as_scoped_manager(client, department_id=er_id)
    queue = await client.get(f"{BASE}/review-queue")
    assert queue.status_code == 200
    assert created.json()["id"] not in [item["id"] for item in queue.json()["change_requests"]]
    requests = await client.get(f"{BASE}/change-requests")
    assert created.json()["id"] not in [item["id"] for item in requests.json()["items"]]
    decision = await client.post(
        f"{BASE}/approval-decisions",
        json={"target_type": "change_request", "target_id": created.json()["id"], "decision": "approved"},
    )
    assert decision.status_code == 403


@pytest.mark.anyio
async def test_scoped_manager_cannot_create_departments(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    er_id = await _demo_department_id(client)
    await login_as_scoped_manager(client, department_id=er_id)

    response = await client.post(f"{BASE}/departments", json={"name": "Radiology", "code": "RAD"})

    assert response.status_code == 403


@pytest.mark.anyio
async def test_worker_cannot_read_other_department_calendar(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    ids = await build_manager_flow(client)
    await client.post("/api/v1/auth/logout")
    await login(client, "worker@guardymed.local")

    assert (await client.get(f"{BASE}/schedule-periods/{ids['period_id']}/calendar")).status_code == 403
    assert (await client.get(f"{BASE}/schedule-periods/{ids['period_id']}")).status_code == 403


@pytest.mark.anyio
async def test_worker_colleagues_expose_names_but_not_documents(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    await client.post("/api/v1/auth/logout")
    session = await login(client, "worker@guardymed.local")

    response = await client.get(f"{BASE}/colleagues")

    assert response.status_code == 200, response.text
    colleagues = response.json()
    assert colleagues and all(set(item) == {"id", "full_name", "worker_type"} for item in colleagues)
    assert session["worker_id"] not in [item["id"] for item in colleagues]


@pytest.mark.anyio
async def test_approval_decision_is_attributed_to_the_signed_in_manager(client: AsyncClient) -> None:
    session = await seed_and_login(client, "manager@guardymed.local")
    queue = await client.get(f"{BASE}/review-queue")
    request_id = queue.json()["change_requests"][0]["id"]

    response = await client.post(
        f"{BASE}/approval-decisions",
        json={"target_type": "change_request", "target_id": request_id, "decision": "rejected", "decided_by": "someone-else"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["decided_by"] == session["user_id"]
    events = await client.get(f"{BASE}/audit-events", params={"entity_id": request_id})
    assert session["user_id"] in {item["actor_id"] for item in events.json()}
