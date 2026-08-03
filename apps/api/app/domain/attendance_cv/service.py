from __future__ import annotations

import math
from datetime import datetime, timezone

from fastapi import HTTPException, status

from apps.api.app.domain.attendance_cv.entities import (
    FaceEmbeddingResult,
    FaceEnrollmentTemplate,
    FaceMatchDecision,
    FaceReviewRoute,
    FaceVector,
)
from apps.api.app.domain.attendance_cv.protocols import FaceEmbeddingRuntime
from apps.api.app.domain.attendance_cv.runtime import DeterministicFaceEmbeddingRuntime


class AttendanceCVService:
    def __init__(
        self,
        runtime: FaceEmbeddingRuntime | None = None,
        *,
        threshold_accept: float = 0.92,
        threshold_review: float = 0.75,
    ) -> None:
        self.runtime = runtime or DeterministicFaceEmbeddingRuntime()
        self.threshold_accept = threshold_accept
        self.threshold_review = threshold_review

    def create_enrollment_template(self, *, worker_id: str, media_bytes: bytes) -> FaceEnrollmentTemplate:
        result = self._embed_or_raise(media_bytes)
        assert result.embedding is not None
        return FaceEnrollmentTemplate(
            id="template_seed",
            enrollment_id="enrollment_seed",
            worker_id=worker_id,
            embedding=result.embedding,
            quality_score=result.quality_score,
            detector_name=result.detector_name,
            model_name=result.model_name,
            created_at=datetime.now(timezone.utc),
        )

    def verify_attempt(
        self,
        *,
        worker_id: str,
        assignment_id: str,
        enrollment_template: FaceEnrollmentTemplate,
        media_bytes: bytes,
    ) -> FaceMatchDecision:
        result = self._embed_or_raise(media_bytes)
        assert result.embedding is not None
        score = self.cosine_similarity(enrollment_template.embedding, result.embedding)
        route = self.route_similarity(score)
        return FaceMatchDecision(
            worker_id=worker_id,
            assignment_id=assignment_id,
            similarity_score=score,
            route=route,
            threshold_accept=self.threshold_accept,
            threshold_review=self.threshold_review,
            detector_name=result.detector_name,
            model_name=result.model_name,
        )

    def route_similarity(self, similarity_score: float) -> FaceReviewRoute:
        if similarity_score >= self.threshold_accept:
            return FaceReviewRoute.ACCEPT
        if similarity_score >= self.threshold_review:
            return FaceReviewRoute.REVIEW
        return FaceReviewRoute.REJECT

    @staticmethod
    def cosine_similarity(left: FaceVector, right: FaceVector) -> float:
        if len(left.values) != len(right.values):
            raise ValueError("face vectors must have the same dimension")
        left_norm = math.sqrt(sum(value * value for value in left.values)) or 1.0
        right_norm = math.sqrt(sum(value * value for value in right.values)) or 1.0
        dot = sum(left_value * right_value for left_value, right_value in zip(left.values, right.values, strict=True))
        return dot / (left_norm * right_norm)

    def _embed_or_raise(self, media_bytes: bytes) -> FaceEmbeddingResult:
        result = self.runtime.embed(media_bytes)
        if not result.face_detected or result.embedding is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="face could not be extracted from media",
            )
        return result
