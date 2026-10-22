import base64

import pytest
from httpx import AsyncClient

from apps.api.app.domain.attendance_cv.entities import FaceEmbeddingResult, FaceReviewRoute, FaceVector
from apps.api.app.domain.attendance_cv.runtime import DeterministicFaceEmbeddingRuntime, demo_capture
from apps.api.app.domain.attendance_cv.service import AttendanceCVService
from tests.conftest import login, seed_and_login

BASE = "/api/v1/scheduling"


# -- runtime / service level -------------------------------------------------


def test_demo_capture_hits_the_requested_cosine() -> None:
    runtime = DeterministicFaceEmbeddingRuntime()
    reference = runtime.embed(demo_capture("wrk_a", 1.0)).embedding
    probe = runtime.embed(demo_capture("wrk_a", 0.62)).embedding

    assert AttendanceCVService.cosine_similarity(reference, probe) == pytest.approx(0.62, abs=1e-6)


def test_different_demo_identities_do_not_match() -> None:
    runtime = DeterministicFaceEmbeddingRuntime()
    reference = runtime.embed(demo_capture("wrk_a", 1.0)).embedding
    stranger = runtime.embed(demo_capture("stranger-at-the-door", 1.0)).embedding

    assert AttendanceCVService.cosine_similarity(reference, stranger) < 0.3


def test_malformed_demo_capture_is_reported_as_unreadable() -> None:
    result = DeterministicFaceEmbeddingRuntime().embed(b"GMDEMO:no-cosine-here")

    assert result.face_detected is False
    assert result.failure == "image_unreadable"


def test_review_threshold_cannot_exceed_accept_threshold() -> None:
    with pytest.raises(ValueError):
        AttendanceCVService(threshold_accept=0.4, threshold_review=0.6)


class _CrowdedFrameRuntime:
    """Pretends two faces are visible and the largest matches perfectly."""

    kind = "stub"
    is_demo = True
    detector_name = "test"
    model_name = "test-model"

    def embed(self, media_bytes: bytes) -> FaceEmbeddingResult:
        return FaceEmbeddingResult(
            face_detected=True,
            quality_score=0.9,
            embedding=FaceVector(values=(1.0, 0.0, 0.0)),
            detector_name=self.detector_name,
            model_name=self.model_name,
            face_count=2,
        )


def test_multiple_faces_are_never_auto_accepted() -> None:
    service = AttendanceCVService(runtime=_CrowdedFrameRuntime())
    template = service.create_enrollment_template(worker_id="wrk_1", media_bytes=b"x" * 32)

    decision = service.verify_attempt(worker_id="wrk_1", assignment_id="asg_1", enrollment_template=template, media_bytes=b"y" * 32)

    assert decision.similarity_score == pytest.approx(1.0)
    assert decision.route == FaceReviewRoute.REVIEW
    assert decision.notes == ("2 faces were visible; the largest was compared",)


def test_template_from_another_model_is_rejected_with_a_clear_code() -> None:
    from fastapi import HTTPException

    service = AttendanceCVService(runtime=_CrowdedFrameRuntime())
    template = service.create_enrollment_template(worker_id="wrk_1", media_bytes=b"x" * 32)
    template.model_name = "some-other-model"

    with pytest.raises(HTTPException) as caught:
        service.verify_attempt(worker_id="wrk_1", assignment_id="asg_1", enrollment_template=template, media_bytes=b"y" * 32)

    assert caught.value.status_code == 409
    assert caught.value.code == "template_model_mismatch"


# -- API level ---------------------------------------------------------------


def b64(payload: bytes) -> str:
    return base64.b64encode(payload).decode("ascii")


async def _enroll_demo_worker(client: AsyncClient) -> tuple[str, dict]:
    """Sign in as the manager, enroll Ana with the demo reference photo, and return (worker_id, captures by id)."""
    await seed_and_login(client, "manager@guardymed.local")
    workers = await client.get(f"{BASE}/workers")
    worker_id = next(item["id"] for item in workers.json() if item["full_name"] == "Ana Ruiz")
    status_response = await client.get(f"{BASE}/attendance/cv/status", params={"worker_id": worker_id})
    captures = {item["id"]: item for item in status_response.json()["demo_captures"]}
    enroll = await client.post(
        f"{BASE}/attendance/cv/enrollments",
        json={"worker_id": worker_id, "media_base64": captures["enroll"]["media_base64"]},
    )
    assert enroll.status_code == 201, enroll.text
    return worker_id, captures


async def _worker_shift(client: AsyncClient) -> str:
    await client.post("/api/v1/auth/logout")
    session = await login(client, "worker@guardymed.local")
    shifts = await client.get(f"{BASE}/workers/{session['worker_id']}/assignments")
    return shifts.json()["items"][0]["id"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("capture", "outcome", "decision"),
    [("clear", "verified", "accepted"), ("borderline", "needs_review", "pending"), ("stranger", "not_verified", "rejected")],
)
async def test_each_demo_capture_produces_its_documented_outcome(client: AsyncClient, capture: str, outcome: str, decision: str) -> None:
    _, captures = await _enroll_demo_worker(client)
    assignment_id = await _worker_shift(client)

    response = await client.post(
        f"{BASE}/attendance/cv/attempts",
        json={"assignment_id": assignment_id, "attempt_type": "check_in", "media_base64": captures[capture]["media_base64"]},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert captures[capture]["expected_outcome"] == outcome
    assert body["match_result"]["outcome"] == outcome
    assert body["match_result"]["is_demo_runtime"] is True
    assert body["attempt"]["decision_status"] == decision
    if outcome == "needs_review":
        assert "needs human review" in body["attempt"]["review_reason"]


@pytest.mark.anyio
async def test_needs_review_attempts_show_up_for_the_manager_and_can_be_decided(client: AsyncClient) -> None:
    _, captures = await _enroll_demo_worker(client)
    assignment_id = await _worker_shift(client)
    attempt = await client.post(
        f"{BASE}/attendance/cv/attempts",
        json={"assignment_id": assignment_id, "attempt_type": "check_in", "media_base64": captures["borderline"]["media_base64"]},
    )
    attempt_id = attempt.json()["attempt"]["id"]

    await client.post("/api/v1/auth/logout")
    await login(client, "manager@guardymed.local")
    queue = await client.get(f"{BASE}/attendance/review-queue")
    assert attempt_id in [item["id"] for item in queue.json()]
    reviewed = await client.patch(
        f"{BASE}/attendance/attempts/{attempt_id}",
        json={"decision_status": "accepted", "review_reason": "Confirmed by the head nurse"},
    )

    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["review_reason"] == "Confirmed by the head nurse"


@pytest.mark.anyio
async def test_unusable_capture_is_a_retry_and_records_nothing(client: AsyncClient) -> None:
    await _enroll_demo_worker(client)
    assignment_id = await _worker_shift(client)

    response = await client.post(
        f"{BASE}/attendance/cv/attempts",
        json={"assignment_id": assignment_id, "attempt_type": "check_in", "media_base64": b64(b"not an image!")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "face_not_detected"
    attempts = await client.get(f"{BASE}/attendance/attempts")
    assert attempts.json() == []


@pytest.mark.anyio
async def test_failed_enrollment_leaves_no_enrollment_behind(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    workers = await client.get(f"{BASE}/workers")
    worker_id = next(item["id"] for item in workers.json() if item["full_name"] == "Rosa Quispe")

    response = await client.post(
        f"{BASE}/attendance/cv/enrollments",
        json={"worker_id": worker_id, "media_base64": b64(b"no face here!!")},
    )

    assert response.status_code == 422
    enrollments = await client.get(f"{BASE}/attendance/enrollments")
    assert worker_id not in [item["worker_id"] for item in enrollments.json()]


@pytest.mark.anyio
async def test_oversized_media_is_rejected(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")
    workers = await client.get(f"{BASE}/workers")

    response = await client.post(
        f"{BASE}/attendance/cv/enrollments",
        json={"worker_id": workers.json()[0]["id"], "media_base64": b64(b"0" * (5 * 1024 * 1024 + 1))},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "media_too_large"


@pytest.mark.anyio
async def test_runtime_status_is_honest_about_the_demo_runtime(client: AsyncClient) -> None:
    await seed_and_login(client, "manager@guardymed.local")

    response = await client.get(f"{BASE}/attendance/cv/status")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["runtime"] == "stub"
    assert body["is_demo"] is True
    assert body["model_name"] == "stub-simulated-embedding"
    assert body["threshold_review"] < body["threshold_accept"]
    assert body["demo_captures"] == []  # no worker in scope, so nothing to simulate


@pytest.mark.anyio
async def test_demo_bootstrap_enrolls_the_demo_worker_so_check_in_works_immediately(client: AsyncClient) -> None:
    await seed_and_login(client, "worker@guardymed.local")

    status_response = await client.get(f"{BASE}/attendance/cv/status")

    body = status_response.json()
    assert body["enrolled"] is True
    clear = next(item for item in body["demo_captures"] if item["id"] == "clear")
    shifts = await client.get(f"{BASE}/workers/{body['worker_id']}/assignments")
    verify = await client.post(
        f"{BASE}/attendance/cv/attempts",
        json={"assignment_id": shifts.json()["items"][0]["id"], "attempt_type": "check_in", "media_base64": clear["media_base64"]},
    )
    assert verify.status_code == 201, verify.text
    assert verify.json()["match_result"]["outcome"] == "verified"
