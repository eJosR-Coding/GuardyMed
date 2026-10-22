import pytest
from httpx import AsyncClient

from apps.api.app.core.config import settings
from tests.conftest import login, seed_and_login

BASE = "/api/v1/scheduling"


async def _pending_request(client: AsyncClient) -> dict:
    queue = await client.get(f"{BASE}/review-queue")
    return queue.json()["change_requests"][0]


@pytest.mark.anyio
async def test_approved_replacement_moves_the_shift_to_the_replacement_worker(client: AsyncClient) -> None:
    manager = await seed_and_login(client, "manager@guardymed.local")
    request = await _pending_request(client)
    assert request["replacement_worker_id"]

    decision = await client.post(
        f"{BASE}/approval-decisions",
        json={"target_type": "change_request", "target_id": request["id"], "decision": "approved", "comment": "Covered"},
    )

    assert decision.status_code == 201, decision.text
    moved = await client.get(f"{BASE}/workers/{request['replacement_worker_id']}/assignments")
    assert request["assignment_id"] in [item["id"] for item in moved.json()["items"]]
    original = await client.get(f"{BASE}/workers/{request['requested_by']}/assignments")
    assert request["assignment_id"] not in [item["id"] for item in original.json()["items"]]
    events = await client.get(f"{BASE}/audit-events", params={"entity_id": request["assignment_id"]})
    reassigned = [item for item in events.json() if item["action"] == "assignment.reassigned"]
    assert reassigned and reassigned[0]["actor_id"] == manager["user_id"]
    assert reassigned[0]["payload"] == {"from_worker_id": request["requested_by"], "to_worker_id": request["replacement_worker_id"]}


@pytest.mark.anyio
async def test_rejected_replacement_keeps_the_original_assignment(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    request = await _pending_request(client)

    decision = await client.post(
        f"{BASE}/approval-decisions",
        json={"target_type": "change_request", "target_id": request["id"], "decision": "rejected"},
    )

    assert decision.status_code == 201, decision.text
    original = await client.get(f"{BASE}/workers/{request['requested_by']}/assignments")
    assert request["assignment_id"] in [item["id"] for item in original.json()["items"]]


@pytest.mark.anyio
async def test_replacement_must_be_a_colleague_from_the_same_department(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    other = await client.post(f"{BASE}/departments", json={"name": "Pediatrics", "code": "PED"})
    outsider = await client.post(
        f"{BASE}/workers",
        json={"full_name": "Pablo Rios", "document_id": "77778888", "worker_type": "Nurse", "department_id": other.json()["id"]},
    )
    await client.post("/api/v1/auth/logout")
    session = await login(client, "worker@guardymed.local")
    shifts = await client.get(f"{BASE}/workers/{session['worker_id']}/assignments")

    response = await client.post(
        f"{BASE}/assignments/{shifts.json()['items'][0]['id']}/change-requests",
        json={"request_type": "replacement", "reason": "Family matter", "replacement_worker_id": outsider.json()["id"]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "replacement worker must belong to the same department"


@pytest.mark.anyio
async def test_export_contains_a_csv_table_of_the_periods_shifts(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    periods = await client.get(f"{BASE}/schedule-periods")
    approved = next(item for item in periods.json()["items"] if item["status"] == "approved")

    response = await client.post(f"{BASE}/schedule-periods/{approved['id']}/exports", json={"export_type": "operational_summary"})

    assert response.status_code == 201, response.text
    content = response.json()["content"]
    header, _, table = content.partition("\n\n")
    assert "export_type=operational_summary" in header
    lines = table.splitlines()
    assert lines[0] == "date,start,end,worker,role,assignment_type,notes"
    assert len(lines) > 30
    assert any("Ana Ruiz" in line for line in lines[1:])


@pytest.mark.anyio
async def test_payroll_export_totals_hours_per_worker(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    periods = await client.get(f"{BASE}/schedule-periods")
    approved = next(item for item in periods.json()["items"] if item["status"] == "approved")

    response = await client.post(f"{BASE}/schedule-periods/{approved['id']}/exports", json={"export_type": "payroll_summary"})

    table = response.json()["content"].partition("\n\n")[2].splitlines()
    assert table[0] == "worker,worker_type,shifts,hours"
    assert len(table) == 6  # header + five workers
    assert all(float(row.rsplit(",", 1)[1]) > 0 for row in table[1:])


@pytest.mark.anyio
async def test_demo_bootstrap_can_be_switched_off(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "demo_mode", False)

    response = await client.post("/api/v1/auth/bootstrap-demo")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
