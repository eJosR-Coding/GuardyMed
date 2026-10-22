from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class FaceReviewRoute(StrEnum):
    ACCEPT = "accept"
    REVIEW = "review"
    REJECT = "reject"


class VerificationOutcome(StrEnum):
    """What the product tells users. Maps 1:1 onto the internal routing decision."""

    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    NOT_VERIFIED = "not_verified"


OUTCOME_BY_ROUTE = {
    FaceReviewRoute.ACCEPT: VerificationOutcome.VERIFIED,
    FaceReviewRoute.REVIEW: VerificationOutcome.NEEDS_REVIEW,
    FaceReviewRoute.REJECT: VerificationOutcome.NOT_VERIFIED,
}


@dataclass(slots=True)
class FaceVector:
    values: tuple[float, ...]


@dataclass(slots=True)
class FaceEmbeddingResult:
    face_detected: bool
    quality_score: float
    embedding: FaceVector | None
    detector_name: str
    model_name: str
    # Why no embedding was produced: "image_unreadable", "no_face" or "low_quality".
    failure: str | None = None
    # Number of faces the detector found; the largest one is used for the embedding.
    face_count: int = 1


@dataclass(slots=True)
class FaceEnrollmentTemplate:
    id: str
    enrollment_id: str
    worker_id: str
    embedding: FaceVector
    quality_score: float
    detector_name: str
    model_name: str
    created_at: datetime


@dataclass(slots=True)
class FaceMatchDecision:
    worker_id: str
    assignment_id: str
    similarity_score: float
    route: FaceReviewRoute
    threshold_accept: float
    threshold_review: float
    detector_name: str
    model_name: str
    # Human-readable reasons the routing was downgraded (for example, several faces in the frame).
    notes: tuple[str, ...] = ()


@dataclass(slots=True)
class PersistedFaceEnrollment:
    id: str
    worker_id: str
    status: str
    created_by: str
    created_at: datetime


@dataclass(slots=True)
class PersistedAttendanceMatchResult:
    id: str
    attempt_id: str
    enrollment_id: str
    similarity_score: float
    route: FaceReviewRoute
    threshold_accept: float
    threshold_review: float
    detector_name: str
    model_name: str
    processed_at: datetime
