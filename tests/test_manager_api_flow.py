import pytest
from httpx import AsyncClient

from tests.conftest import build_manager_flow, login, seed_and_login


@pytest.mark.anyio
async def test_manager_can_create_department_worker_period_assignment_and_load_calendar(client: AsyncClient) -> None:
    session = await seed_and_login(client, "manager@guardymed.local")
    assert session["role"] == "manager"

    ids = await build_manager_flow(client)

    calendar = await client.get(f"/api/v1/scheduling/schedule-periods/{ids['period_id']}/calendar")
    assert calendar.status_code == 200, calendar.text
    data = calendar.json()
    assert data["period"]["id"] == ids["period_id"]
    assert len(data["assignments"]) == 1
    assert data["assignments"][0]["worker_id"] == ids["worker_id"]


@pytest.mark.anyio
async def test_manager_conflicts_are_reported_for_duplicate_department_period_and_overlap(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    ids = await build_manager_flow(client)

    duplicate_department = await client.post(
        "/api/v1/scheduling/departments",
        json={"name": "Pediatrics 2", "code": "PED"},
    )
    assert duplicate_department.status_code == 409

    duplicate_period = await client.post(
        "/api/v1/scheduling/schedule-periods",
        json={"year": 2026, "month": 9, "department_id": ids["department_id"]},
    )
    assert duplicate_period.status_code == 409

    overlapping_assignment = await client.post(
        f"/api/v1/scheduling/schedule-periods/{ids['period_id']}/assignments",
        json={
            "worker_id": ids["worker_id"],
            "assignment_type": "shift_lead",
            "shift_date": "2026-09-03",
            "start_time": "12:00:00",
            "end_time": "18:00:00",
            "notes": "Overlap",
        },
    )
    assert overlapping_assignment.status_code == 409


@pytest.mark.anyio
async def test_worker_can_only_see_own_assignments_and_can_create_and_cancel_request(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    ids = await build_manager_flow(client)
    await client.post("/api/v1/auth/logout")

    worker_session = await login(client, "worker@guardymed.local")
    own_assignments = await client.get(f"/api/v1/scheduling/workers/{worker_session['worker_id']}/assignments")
    assert own_assignments.status_code == 200, own_assignments.text

    other_assignments = await client.get(f"/api/v1/scheduling/workers/{ids['worker_id']}/assignments")
    assert other_assignments.status_code == 403

    own_request = await client.post(
        f"/api/v1/scheduling/assignments/{own_assignments.json()['items'][0]['id']}/change-requests",
        json={
            "request_type": "adjustment",
            "reason": "Medical appointment",
            "replacement_worker_id": None,
        },
    )
    assert own_request.status_code == 201, own_request.text
    request_id = own_request.json()["id"]

    listed_requests = await client.get("/api/v1/scheduling/change-requests")
    assert listed_requests.status_code == 200
    assert all(item["requested_by"] == worker_session["worker_id"] for item in listed_requests.json()["items"])

    cancel = await client.patch(
        f"/api/v1/scheduling/change-requests/{request_id}",
        json={"status": "cancelled"},
    )
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"


@pytest.mark.anyio
async def test_worker_cannot_create_request_for_someone_elses_assignment(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    ids = await build_manager_flow(client)
    await client.post("/api/v1/auth/logout")

    worker_session = await login(client, "worker@guardymed.local")
    assert worker_session["worker_id"] != ids["worker_id"]

    forbidden_request = await client.post(
        f"/api/v1/scheduling/assignments/{ids['assignment_id']}/change-requests",
        json={
            "request_type": "swap",
            "reason": "Trying to request for someone else",
            "replacement_worker_id": None,
        },
    )
    assert forbidden_request.status_code == 403


@pytest.mark.anyio
async def test_manager_can_review_period_and_export_after_approval(client: AsyncClient) -> None:
    manager = await seed_and_login(client, "manager@guardymed.local")

    worker = await client.post(
        "/api/v1/scheduling/workers",
        json={
            "full_name": "Rosa Diaz",
            "document_id": "90909090",
            "worker_type": "Nurse",
            "department_id": manager["department_id"],
        },
    )
    assert worker.status_code == 201, worker.text
    worker_id = worker.json()["id"]

    period = await client.post(
        "/api/v1/scheduling/schedule-periods",
        json={
            "year": 2026,
            "month": 10,
            "department_id": manager["department_id"],
        },
    )
    assert period.status_code == 201, period.text
    period_id = period.json()["id"]

    assignment = await client.post(
        f"/api/v1/scheduling/schedule-periods/{period_id}/assignments",
        json={
            "worker_id": worker_id,
            "assignment_type": "guard_shift",
            "shift_date": "2026-10-03",
            "start_time": "08:00:00",
            "end_time": "20:00:00",
            "notes": "Manager-visible coverage",
        },
    )
    assert assignment.status_code == 201, assignment.text

    send_to_review = await client.patch(
        f"/api/v1/scheduling/schedule-periods/{period_id}",
        json={"status": "in_review"},
    )
    assert send_to_review.status_code == 200, send_to_review.text

    export_before_approval = await client.post(
        f"/api/v1/scheduling/schedule-periods/{period_id}/exports",
        json={"export_type": "compliance_report"},
    )
    assert export_before_approval.status_code == 409

    queue = await client.get("/api/v1/scheduling/review-queue")
    assert queue.status_code == 200, queue.text
    assert any(item["id"] == period_id for item in queue.json()["schedule_periods"])

    decision = await client.post(
        "/api/v1/scheduling/approval-decisions",
        json={
            "target_type": "schedule_period",
            "target_id": period_id,
            "decision": "approved",
            "comment": "Approved in test",
        },
    )
    assert decision.status_code == 201, decision.text

    export = await client.post(
        f"/api/v1/scheduling/schedule-periods/{period_id}/exports",
        json={"export_type": "compliance_report"},
    )
    assert export.status_code == 201, export.text


@pytest.mark.anyio
async def test_manager_can_reject_change_request_and_it_leaves_review_queue(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    await client.post("/api/v1/auth/logout")

    worker_session = await login(client, "worker@guardymed.local")
    assignments = await client.get(f"/api/v1/scheduling/workers/{worker_session['worker_id']}/assignments")
    assignment_id = assignments.json()["items"][0]["id"]

    request = await client.post(
        f"/api/v1/scheduling/assignments/{assignment_id}/change-requests",
        json={
            "request_type": "incident",
            "reason": "Need escalation",
            "replacement_worker_id": None,
        },
    )
    assert request.status_code == 201, request.text
    request_id = request.json()["id"]
    await client.post("/api/v1/auth/logout")

    await login(client, "manager@guardymed.local")
    reject = await client.post(
        "/api/v1/scheduling/approval-decisions",
        json={
            "target_type": "change_request",
            "target_id": request_id,
            "decision": "rejected",
            "comment": "Rejected in test",
        },
    )
    assert reject.status_code == 201, reject.text

    queue_after = await client.get("/api/v1/scheduling/review-queue")
    assert queue_after.status_code == 200
    assert all(item["id"] != request_id for item in queue_after.json()["change_requests"])


@pytest.mark.anyio
async def test_manager_can_review_attendance_and_worker_cannot_access_review_queue(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    await client.post("/api/v1/auth/logout")

    worker_session = await login(client, "worker@guardymed.local")
    assignments = await client.get(f"/api/v1/scheduling/workers/{worker_session['worker_id']}/assignments")
    assignment_id = assignments.json()["items"][0]["id"]

    attempt = await client.post(
        "/api/v1/scheduling/attendance/attempts",
        json={
            "assignment_id": assignment_id,
            "attempt_type": "check_in",
            "evidence_ref": "manual://worker-selfie",
        },
    )
    assert attempt.status_code == 201, attempt.text
    attempt_id = attempt.json()["id"]

    worker_cannot_review = await client.get("/api/v1/scheduling/review-queue")
    assert worker_cannot_review.status_code == 403

    await client.post("/api/v1/auth/logout")
    await login(client, "manager@guardymed.local")

    review = await client.patch(
        f"/api/v1/scheduling/attendance/attempts/{attempt_id}",
        json={"decision_status": "accepted", "review_reason": "Looks valid"},
    )
    assert review.status_code == 200, review.text
    assert review.json()["decision_status"] == "accepted"
