from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class FaceReviewRoute(StrEnum):
    ACCEPT = "accept"
    REVIEW = "review"
    REJECT = "reject"


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
