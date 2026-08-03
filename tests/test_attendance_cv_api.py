import base64

import pytest
from httpx import AsyncClient

from tests.conftest import login, seed_and_login


def encode_media(payload: bytes) -> str:
    return base64.b64encode(payload).decode("ascii")


@pytest.mark.anyio
async def test_manager_can_create_face_enrollment_for_demo_worker(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")

    workers = await client.get("/api/v1/scheduling/workers")
    assert workers.status_code == 200, workers.text
    worker_id = workers.json()[0]["id"]

    response = await client.post(
        "/api/v1/scheduling/attendance/cv/enrollments",
        json={
            "worker_id": worker_id,
            "media_base64": encode_media(b"worker-face-enrollment-seed-0001"),
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["enrollment"]["worker_id"] == worker_id
    assert data["template"]["worker_id"] == worker_id
    assert data["template"]["detector_name"]


@pytest.mark.anyio
async def test_worker_can_submit_face_verification_for_own_assignment(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")

    workers = await client.get("/api/v1/scheduling/workers")
    assert workers.status_code == 200, workers.text
    worker_id = workers.json()[0]["id"]

    enrollment_media = encode_media(b"worker-face-verification-seed-0002")
    enroll = await client.post(
        "/api/v1/scheduling/attendance/cv/enrollments",
        json={"worker_id": worker_id, "media_base64": enrollment_media},
    )
    assert enroll.status_code == 201, enroll.text

    await client.post("/api/v1/auth/logout")
    worker_session = await login(client, "worker@guardymed.local")
    assignments = await client.get(f"/api/v1/scheduling/workers/{worker_session['worker_id']}/assignments")
    assert assignments.status_code == 200, assignments.text
    assignment_id = assignments.json()["items"][0]["id"]

    verify = await client.post(
        "/api/v1/scheduling/attendance/cv/attempts",
        json={
            "assignment_id": assignment_id,
            "attempt_type": "check_in",
            "media_base64": enrollment_media,
        },
    )
    assert verify.status_code == 201, verify.text
    data = verify.json()
    assert data["attempt"]["assignment_id"] == assignment_id
    assert data["match_result"]["similarity_score"] == pytest.approx(1.0)
    assert data["match_result"]["route"] == "accept"
    assert data["attempt"]["decision_status"] == "accepted"


@pytest.mark.anyio
async def test_worker_face_verification_requires_existing_face_enrollment(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    await client.post("/api/v1/auth/logout")

    worker_session = await login(client, "worker@guardymed.local")
    assignments = await client.get(f"/api/v1/scheduling/workers/{worker_session['worker_id']}/assignments")
    assert assignments.status_code == 200, assignments.text
    assignment_id = assignments.json()["items"][0]["id"]

    verify = await client.post(
        "/api/v1/scheduling/attendance/cv/attempts",
        json={
            "assignment_id": assignment_id,
            "attempt_type": "check_in",
            "media_base64": encode_media(b"worker-face-verification-seed-0003"),
        },
    )
    assert verify.status_code == 409
    assert verify.json()["detail"] == "face enrollment not found for worker"
