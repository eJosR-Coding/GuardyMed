import pytest
from httpx import AsyncClient

from apps.api.app.api.auth import UserRole, create_user
from tests.conftest import build_coordinator_flow, login, seed_and_login


@pytest.mark.anyio
async def test_coordinator_can_create_department_worker_period_assignment_and_load_calendar(client: AsyncClient) -> None:
    session = await seed_and_login(client, "coord@guardymed.local")
    assert session["role"] == "coordinator"

    ids = await build_coordinator_flow(client)

    calendar = await client.get(f"/api/v1/scheduling/schedule-periods/{ids['period_id']}/calendar")
    assert calendar.status_code == 200, calendar.text
    data = calendar.json()
    assert data["period"]["id"] == ids["period_id"]
    assert len(data["assignments"]) == 1
    assert data["assignments"][0]["worker_id"] == ids["worker_id"]


@pytest.mark.anyio
async def test_coordinator_conflicts_are_reported_for_duplicate_department_period_and_overlap(client: AsyncClient) -> None:
    await seed_and_login(client, "coord@guardymed.local")
    ids = await build_coordinator_flow(client)

    duplicate_department = await client.post(
        "/api/v1/scheduling/departments",
        json={"name": "Pediatrics 2", "code": "PED"},
    )
    assert duplicate_department.status_code == 409
    assert duplicate_department.json()["detail"] == "department code already exists"

    duplicate_period = await client.post(
        "/api/v1/scheduling/schedule-periods",
        json={"year": 2026, "month": 9, "department_id": ids["department_id"]},
    )
    assert duplicate_period.status_code == 409
    assert duplicate_period.json()["detail"] == "schedule period already exists for department and month"

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
    assert overlapping_assignment.json()["detail"] == "worker already has an overlapping assignment"


@pytest.mark.anyio
async def test_worker_can_only_see_own_assignments_and_can_create_and_cancel_request(client: AsyncClient) -> None:
    await seed_and_login(client, "coord@guardymed.local")
    ids = await build_coordinator_flow(client)
    await client.post("/api/v1/auth/logout")

    worker_session = await login(client, "worker@guardymed.local")
    assert worker_session["role"] == "worker"

    own_assignments = await client.get(f"/api/v1/scheduling/workers/{worker_session['worker_id']}/assignments")
    assert own_assignments.status_code == 200, own_assignments.text
    assert {item["worker_id"] for item in own_assignments.json()["items"]} == {worker_session["worker_id"]}

    other_assignments = await client.get(f"/api/v1/scheduling/workers/{ids['worker_id']}/assignments")
    assert other_assignments.status_code == 403
    assert other_assignments.json()["detail"] == "forbidden"

    request = await client.post(
        "/api/v1/scheduling/assignments/asg_missing/change-requests",
        json={
            "request_type": "swap",
            "reason": "Need a swap",
            "replacement_worker_id": None,
        },
    )
    assert request.status_code == 404

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
    assert len(listed_requests.json()["items"]) >= 1
    assert all(item["requested_by"] == worker_session["worker_id"] for item in listed_requests.json()["items"])

    cancel = await client.patch(
        f"/api/v1/scheduling/change-requests/{request_id}",
        json={"status": "cancelled"},
    )
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"

    forbidden_status_change = await client.patch(
        f"/api/v1/scheduling/change-requests/{request_id}",
        json={"status": "approved"},
    )
    assert forbidden_status_change.status_code == 403
    assert forbidden_status_change.json()["detail"] == "workers may only cancel their own pending requests"


@pytest.mark.anyio
async def test_worker_cannot_create_request_for_someone_elses_assignment(client: AsyncClient) -> None:
    await seed_and_login(client, "coord@guardymed.local")
    ids = await build_coordinator_flow(client)
    await client.post("/api/v1/auth/logout")

    worker_session = await login(client, "worker@guardymed.local")
    assert worker_session["role"] == "worker"
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
    assert forbidden_request.json()["detail"] == "worker can only request changes for own assignments"


@pytest.mark.anyio
async def test_approver_can_review_period_and_export_after_approval(client: AsyncClient) -> None:
    coordinator = await seed_and_login(client, "coord@guardymed.local")

    worker = await client.post(
        "/api/v1/scheduling/workers",
        json={
            "full_name": "Rosa Diaz",
            "document_id": "90909090",
            "worker_type": "Nurse",
            "department_id": coordinator["department_id"],
        },
    )
    assert worker.status_code == 201, worker.text
    worker_id = worker.json()["id"]

    period = await client.post(
        "/api/v1/scheduling/schedule-periods",
        json={
            "year": 2026,
            "month": 10,
            "department_id": coordinator["department_id"],
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
            "notes": "Approver-visible coverage",
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
    assert export_before_approval.json()["detail"] == "schedule period must be approved before export"

    await client.post("/api/v1/auth/logout")
    approver_session = await login(client, "approver@guardymed.local")
    assert approver_session["role"] == "approver"

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

    approved_calendar = await client.get(f"/api/v1/scheduling/schedule-periods/{period_id}/calendar")
    assert approved_calendar.status_code == 200
    assert approved_calendar.json()["period"]["status"] == "approved"

    export = await client.post(
        f"/api/v1/scheduling/schedule-periods/{period_id}/exports",
        json={"export_type": "compliance_report"},
    )
    assert export.status_code == 201, export.text

    exports = await client.get(f"/api/v1/scheduling/schedule-periods/{period_id}/exports")
    assert exports.status_code == 200
    assert len(exports.json()) == 1


@pytest.mark.anyio
async def test_approver_can_reject_change_request_and_it_leaves_review_queue(client: AsyncClient) -> None:
    await seed_and_login(client, "coord@guardymed.local")
    await client.post("/api/v1/auth/logout")

    worker_session = await login(client, "worker@guardymed.local")
    assignments = await client.get(f"/api/v1/scheduling/workers/{worker_session['worker_id']}/assignments")
    assert assignments.status_code == 200, assignments.text
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

    approver_session = await login(client, "approver@guardymed.local")
    assert approver_session["role"] == "approver"

    queue_before = await client.get("/api/v1/scheduling/review-queue")
    assert queue_before.status_code == 200, queue_before.text
    assert any(item["id"] == request_id for item in queue_before.json()["change_requests"])

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

    request_after = await client.get(f"/api/v1/scheduling/change-requests/{request_id}")
    assert request_after.status_code == 200, request_after.text
    assert request_after.json()["status"] == "rejected"

    queue_after = await client.get("/api/v1/scheduling/review-queue")
    assert queue_after.status_code == 200, queue_after.text
    assert not any(item["id"] == request_id for item in queue_after.json()["change_requests"])


@pytest.mark.anyio
async def test_coordinator_cannot_edit_assignments_after_period_leaves_draft(client: AsyncClient) -> None:
    await seed_and_login(client, "coord@guardymed.local")
    ids = await build_coordinator_flow(client)

    send_to_review = await client.patch(
        f"/api/v1/scheduling/schedule-periods/{ids['period_id']}",
        json={"status": "in_review"},
    )
    assert send_to_review.status_code == 200, send_to_review.text

    create_after_review = await client.post(
        f"/api/v1/scheduling/schedule-periods/{ids['period_id']}/assignments",
        json={
            "worker_id": ids["worker_id"],
            "assignment_type": "shift_lead",
            "shift_date": "2026-09-04",
            "start_time": "08:00:00",
            "end_time": "20:00:00",
            "notes": "Should fail after draft",
        },
    )
    assert create_after_review.status_code == 409
    assert create_after_review.json()["detail"] == "schedule period must be draft to edit assignments"


@pytest.mark.anyio
async def test_audit_trail_contains_core_events_for_coordinator_flow(client: AsyncClient) -> None:
    await seed_and_login(client, "coord@guardymed.local")
    ids = await build_coordinator_flow(client)

    review = await client.patch(
        f"/api/v1/scheduling/schedule-periods/{ids['period_id']}",
        json={"status": "in_review"},
    )
    assert review.status_code == 200, review.text

    events = await client.get("/api/v1/scheduling/audit-events")
    assert events.status_code == 200, events.text
    payload = events.json()

    actions = {item["action"] for item in payload}
    assert "department.created" in actions
    assert "worker.created" in actions
    assert "schedule_period.created" in actions
    assert "assignment.created" in actions
    assert "schedule_period.status_updated" in actions

    assignment_events = [item for item in payload if item["entity_type"] == "assignment" and item["entity_id"] == ids["assignment_id"]]
    assert assignment_events
    assert assignment_events[0]["payload"]["worker_id"] == ids["worker_id"]
    assert assignment_events[0]["payload"]["schedule_period_id"] == ids["period_id"]


@pytest.mark.anyio
async def test_export_content_matches_period_and_assignment_counts(client: AsyncClient) -> None:
    coordinator = await seed_and_login(client, "coord@guardymed.local")

    worker = await client.post(
        "/api/v1/scheduling/workers",
        json={
            "full_name": "Julia Ramos",
            "document_id": "66667777",
            "worker_type": "Nurse",
            "department_id": coordinator["department_id"],
        },
    )
    assert worker.status_code == 201, worker.text
    worker_id = worker.json()["id"]

    period = await client.post(
        "/api/v1/scheduling/schedule-periods",
        json={
            "year": 2026,
            "month": 11,
            "department_id": coordinator["department_id"],
        },
    )
    assert period.status_code == 201, period.text
    period_id = period.json()["id"]

    assignment = await client.post(
        f"/api/v1/scheduling/schedule-periods/{period_id}/assignments",
        json={
            "worker_id": worker_id,
            "assignment_type": "guard_shift",
            "shift_date": "2026-11-02",
            "start_time": "08:00:00",
            "end_time": "20:00:00",
            "notes": "Export coverage",
        },
    )
    assert assignment.status_code == 201, assignment.text

    review = await client.patch(
        f"/api/v1/scheduling/schedule-periods/{period_id}",
        json={"status": "in_review"},
    )
    assert review.status_code == 200, review.text

    await client.post("/api/v1/auth/logout")
    await login(client, "approver@guardymed.local")

    approve = await client.post(
        "/api/v1/scheduling/approval-decisions",
        json={
            "target_type": "schedule_period",
            "target_id": period_id,
            "decision": "approved",
            "comment": "Approve for export validation",
        },
    )
    assert approve.status_code == 201, approve.text

    export = await client.post(
        f"/api/v1/scheduling/schedule-periods/{period_id}/exports",
        json={"export_type": "compliance_report"},
    )
    assert export.status_code == 201, export.text

    content = export.json()["content"]
    lines = content.splitlines()
    assert "export_type=compliance_report" in lines
    assert "period=2026-11" in lines
    assert f"department_id={coordinator['department_id']}" in lines
    assert "assignments=1" in lines
    assert "workers=1" in lines


@pytest.mark.anyio
async def test_approver_queue_excludes_out_of_scope_periods_and_requests(client: AsyncClient) -> None:
    await seed_and_login(client, "coord@guardymed.local")
    ids = await build_coordinator_flow(client)

    ped_worker_user = create_user(
        email="carla@guardymed.local",
        full_name="Carla Mendez",
        password="password123",
        role=UserRole.WORKER,
        worker_id=ids["worker_id"],
        department_id=ids["department_id"],
    )
    assert ped_worker_user.worker_id == ids["worker_id"]

    review = await client.patch(
        f"/api/v1/scheduling/schedule-periods/{ids['period_id']}",
        json={"status": "in_review"},
    )
    assert review.status_code == 200, review.text

    await client.post("/api/v1/auth/logout")
    await login(client, "carla@guardymed.local")
    ped_request = await client.post(
        f"/api/v1/scheduling/assignments/{ids['assignment_id']}/change-requests",
        json={
            "request_type": "swap",
            "reason": "Out of scope request",
            "replacement_worker_id": None,
        },
    )
    assert ped_request.status_code == 201, ped_request.text
    ped_request_id = ped_request.json()["id"]

    await client.post("/api/v1/auth/logout")
    await login(client, "approver@guardymed.local")

    queue = await client.get("/api/v1/scheduling/review-queue")
    assert queue.status_code == 200, queue.text
    assert not any(item["id"] == ids["period_id"] for item in queue.json()["schedule_periods"])
    assert not any(item["id"] == ped_request_id for item in queue.json()["change_requests"])

    listed_requests = await client.get("/api/v1/scheduling/change-requests")
    assert listed_requests.status_code == 200, listed_requests.text
    assert not any(item["id"] == ped_request_id for item in listed_requests.json()["items"])


@pytest.mark.anyio
async def test_approver_cannot_access_or_decide_out_of_scope_resources(client: AsyncClient) -> None:
    await seed_and_login(client, "coord@guardymed.local")
    ids = await build_coordinator_flow(client)

    ped_worker_user = create_user(
        email="ped-worker@guardymed.local",
        full_name="Carla Mendez",
        password="password123",
        role=UserRole.WORKER,
        worker_id=ids["worker_id"],
        department_id=ids["department_id"],
    )
    assert ped_worker_user.worker_id == ids["worker_id"]

    review = await client.patch(
        f"/api/v1/scheduling/schedule-periods/{ids['period_id']}",
        json={"status": "in_review"},
    )
    assert review.status_code == 200, review.text

    await client.post("/api/v1/auth/logout")
    await login(client, "ped-worker@guardymed.local")
    ped_request = await client.post(
        f"/api/v1/scheduling/assignments/{ids['assignment_id']}/change-requests",
        json={
            "request_type": "incident",
            "reason": "PED request",
            "replacement_worker_id": None,
        },
    )
    assert ped_request.status_code == 201, ped_request.text
    ped_request_id = ped_request.json()["id"]

    await client.post("/api/v1/auth/logout")
    await login(client, "approver@guardymed.local")

    calendar = await client.get(f"/api/v1/scheduling/schedule-periods/{ids['period_id']}/calendar")
    assert calendar.status_code == 403

    request = await client.get(f"/api/v1/scheduling/change-requests/{ped_request_id}")
    assert request.status_code == 403

    approve_period = await client.post(
        "/api/v1/scheduling/approval-decisions",
        json={
            "target_type": "schedule_period",
            "target_id": ids["period_id"],
            "decision": "approved",
            "comment": "Should be forbidden",
        },
    )
    assert approve_period.status_code == 403

    reject_request = await client.post(
        "/api/v1/scheduling/approval-decisions",
        json={
            "target_type": "change_request",
            "target_id": ped_request_id,
            "decision": "rejected",
            "comment": "Should be forbidden",
        },
    )
    assert reject_request.status_code == 403


@pytest.mark.anyio
async def test_role_forbidden_matrix_for_core_actions(client: AsyncClient) -> None:
    await seed_and_login(client, "worker@guardymed.local")

    worker_cannot_create_department = await client.post(
        "/api/v1/scheduling/departments",
        json={"name": "Lab", "code": "LAB"},
    )
    assert worker_cannot_create_department.status_code == 403

    worker_cannot_review = await client.get("/api/v1/scheduling/review-queue")
    assert worker_cannot_review.status_code == 403

    await client.post("/api/v1/auth/logout")
    await login(client, "approver@guardymed.local")

    approver_cannot_create_period = await client.post(
        "/api/v1/scheduling/schedule-periods",
        json={"year": 2026, "month": 10, "department_id": "dep_missing"},
    )
    assert approver_cannot_create_period.status_code == 403
