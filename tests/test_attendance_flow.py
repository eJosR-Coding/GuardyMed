import pytest
from httpx import AsyncClient

from tests.conftest import build_manager_flow, login, seed_and_login


@pytest.mark.anyio
async def test_manager_can_create_attendance_enrollment_for_worker(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    ids = await build_manager_flow(client)

    response = await client.post(
        "/api/v1/scheduling/attendance/enrollments",
        json={"worker_id": ids["worker_id"]},
    )

    assert response.status_code == 201, response.text
    assert response.json()["worker_id"] == ids["worker_id"]
    assert response.json()["status"] == "active"


@pytest.mark.anyio
async def test_worker_can_submit_attendance_for_own_assignment(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    await client.post("/api/v1/auth/logout")

    session = await login(client, "worker@guardymed.local")
    assignments = await client.get(f"/api/v1/scheduling/workers/{session['worker_id']}/assignments")
    assignment_id = assignments.json()["items"][0]["id"]

    response = await client.post(
        "/api/v1/scheduling/attendance/attempts",
        json={
            "assignment_id": assignment_id,
            "attempt_type": "check_out",
            "evidence_ref": "manual://selfie-out",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["worker_id"] == session["worker_id"]
    assert response.json()["decision_status"] == "pending"

    attempts = await client.get("/api/v1/scheduling/attendance/attempts")
    assert attempts.status_code == 200, attempts.text
    assert all(item["worker_id"] == session["worker_id"] for item in attempts.json())


@pytest.mark.anyio
async def test_worker_cannot_submit_attendance_for_someone_elses_assignment(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    ids = await build_manager_flow(client)
    await client.post("/api/v1/auth/logout")

    session = await login(client, "worker@guardymed.local")
    assert session["worker_id"] != ids["worker_id"]

    response = await client.post(
        "/api/v1/scheduling/attendance/attempts",
        json={
            "assignment_id": ids["assignment_id"],
            "attempt_type": "check_in",
            "evidence_ref": "manual://wrong-worker",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "worker can only submit attendance for own assignments"


@pytest.mark.anyio
async def test_manager_can_review_pending_attendance_attempt(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    await client.post("/api/v1/auth/logout")

    worker_session = await login(client, "worker@guardymed.local")
    assignments = await client.get(f"/api/v1/scheduling/workers/{worker_session['worker_id']}/assignments")
    assignment_id = assignments.json()["items"][0]["id"]

    created = await client.post(
        "/api/v1/scheduling/attendance/attempts",
        json={
            "assignment_id": assignment_id,
            "attempt_type": "check_out",
            "evidence_ref": "manual://review-me",
        },
    )
    attempt_id = created.json()["id"]
    await client.post("/api/v1/auth/logout")

    await login(client, "manager@guardymed.local")
    queue = await client.get("/api/v1/scheduling/attendance/review-queue")
    assert queue.status_code == 200, queue.text
    assert any(item["id"] == attempt_id for item in queue.json())

    reviewed = await client.patch(
        f"/api/v1/scheduling/attendance/attempts/{attempt_id}",
        json={"decision_status": "accepted", "review_reason": "manual match ok"},
    )

    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["decision_status"] == "accepted"
    assert reviewed.json()["review_reason"] == "manual match ok"
