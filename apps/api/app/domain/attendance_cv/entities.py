from __future__ import annotations

from dataclasses import dataclass
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
    worker_id: str
    embedding: FaceVector
    quality_score: float
    detector_name: str
    model_name: str


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
