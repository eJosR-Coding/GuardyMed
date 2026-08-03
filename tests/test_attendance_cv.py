import pytest
from fastapi import HTTPException

from apps.api.app.domain.attendance_cv.entities import FaceReviewRoute, FaceVector
from apps.api.app.domain.attendance_cv.service import AttendanceCVService


def test_create_enrollment_template_returns_embedding_and_metadata() -> None:
    service = AttendanceCVService()

    template = service.create_enrollment_template(
        worker_id="wrk_123",
        media_bytes=b"worker-face-enrollment-sample-001",
    )

    assert template.worker_id == "wrk_123"
    assert template.detector_name == "stub-face-detector"
    assert template.model_name == "stub-arcface-embedding"
    assert len(template.embedding.values) == 16
    assert template.quality_score > 0.0


def test_same_media_produces_accept_route() -> None:
    service = AttendanceCVService()
    media = b"worker-face-enrollment-sample-001"
    template = service.create_enrollment_template(worker_id="wrk_123", media_bytes=media)

    decision = service.verify_attempt(
        worker_id="wrk_123",
        assignment_id="asg_123",
        enrollment_template=template,
        media_bytes=media,
    )

    assert decision.route == FaceReviewRoute.ACCEPT
    assert decision.similarity_score == pytest.approx(1.0)


def test_threshold_routing_covers_review_and_reject() -> None:
    service = AttendanceCVService(threshold_accept=0.9, threshold_review=0.75)

    assert service.route_similarity(0.95) == FaceReviewRoute.ACCEPT
    assert service.route_similarity(0.80) == FaceReviewRoute.REVIEW
    assert service.route_similarity(0.20) == FaceReviewRoute.REJECT


def test_cosine_similarity_rejects_dimension_mismatch() -> None:
    left = FaceVector(values=(1.0, 0.0))
    right = FaceVector(values=(1.0, 0.0, 0.0))

    with pytest.raises(ValueError):
        AttendanceCVService.cosine_similarity(left, right)


def test_invalid_media_raises_http_error() -> None:
    service = AttendanceCVService()

    with pytest.raises(HTTPException) as exc_info:
        service.create_enrollment_template(worker_id="wrk_123", media_bytes=b"short")

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "face could not be extracted from media"
