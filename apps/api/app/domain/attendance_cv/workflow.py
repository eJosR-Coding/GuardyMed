from __future__ import annotations

import base64
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status

from apps.api.app.core.errors import ApiError
from apps.api.app.domain.attendance_cv.entities import (
    FaceEnrollmentTemplate,
    FaceReviewRoute,
    PersistedAttendanceMatchResult,
    PersistedFaceEnrollment,
)
from apps.api.app.domain.attendance_cv.repository import SQLAlchemyAttendanceCVRepository
from apps.api.app.domain.attendance_cv.service import AttendanceCVService
from apps.api.app.domain.scheduling import service as scheduling_service
from apps.api.app.domain.scheduling.entities import AttendanceAttempt, AttendanceAttemptType, AttendanceDecisionStatus

CV_ACTOR_ID = "system_cv"
MAX_MEDIA_BYTES = 5 * 1024 * 1024


class AttendanceCVWorkflow:
    def __init__(
        self,
        *,
        repository: SQLAlchemyAttendanceCVRepository,
        cv_service: AttendanceCVService,
    ) -> None:
        self.repository = repository
        self.cv_service = cv_service

    def create_enrollment(self, *, worker_id: str, created_by: str, media_base64: str) -> tuple[PersistedFaceEnrollment, FaceEnrollmentTemplate]:
        scheduling_service._require_worker(worker_id)
        media_bytes = self._decode_media(media_base64)
        # Extract the embedding first: a photo without a usable face must not leave a half-created enrollment behind.
        template_seed = self.cv_service.create_enrollment_template(worker_id=worker_id, media_bytes=media_bytes)

        if scheduling_service.repository.get_attendance_enrollment_by_worker(worker_id) is None:
            scheduling_service.create_attendance_enrollment(worker_id=worker_id, created_by=created_by)
        persisted = PersistedFaceEnrollment(
            id=self._new_id("fen"),
            worker_id=worker_id,
            status="active",
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
        )
        self.repository.create_face_enrollment(persisted)
        template = FaceEnrollmentTemplate(
            id=self._new_id("ftp"),
            enrollment_id=persisted.id,
            worker_id=worker_id,
            embedding=template_seed.embedding,
            quality_score=template_seed.quality_score,
            detector_name=template_seed.detector_name,
            model_name=template_seed.model_name,
            created_at=datetime.now(timezone.utc),
        )
        self.repository.create_face_template(template)
        scheduling_service.record_event(
            actor_id=created_by,
            entity_type="face_enrollment",
            entity_id=persisted.id,
            action="face_enrollment.created",
            payload={"worker_id": worker_id, "model_name": template.model_name, "quality_score": round(template.quality_score, 3)},
        )
        return persisted, template

    def has_face_template(self, worker_id: str) -> bool:
        return self.repository.get_latest_template_for_worker(worker_id) is not None

    def verify_assignment_attempt(
        self,
        *,
        worker_id: str,
        assignment_id: str,
        attempt_type: AttendanceAttemptType,
        media_base64: str,
    ) -> tuple[AttendanceAttempt, PersistedAttendanceMatchResult]:
        assignment = scheduling_service.get_assignment(assignment_id)
        if assignment.worker_id != worker_id:
            raise ApiError(status.HTTP_403_FORBIDDEN, "worker can only submit attendance for own assignments", code="forbidden")

        template = self.repository.get_latest_template_for_worker(worker_id)
        if template is None:
            raise ApiError(status.HTTP_409_CONFLICT, "face enrollment not found for worker", code="conflict")

        media_bytes = self._decode_media(media_base64)
        # Compare first, record afterwards: an unreadable capture is a retry, not an attendance attempt.
        decision = self.cv_service.verify_attempt(
            worker_id=worker_id,
            assignment_id=assignment_id,
            enrollment_template=template,
            media_bytes=media_bytes,
        )
        attempt = scheduling_service.create_attendance_attempt(
            worker_id=worker_id,
            assignment_id=assignment_id,
            attempt_type=attempt_type,
            evidence_ref="cv://inline-capture",
        )
        result = PersistedAttendanceMatchResult(
            id=self._new_id("amr"),
            attempt_id=attempt.id,
            enrollment_id=template.enrollment_id,
            similarity_score=decision.similarity_score,
            route=decision.route,
            threshold_accept=decision.threshold_accept,
            threshold_review=decision.threshold_review,
            detector_name=decision.detector_name,
            model_name=decision.model_name,
            processed_at=datetime.now(timezone.utc),
        )
        self.repository.create_match_result(result)

        score = f"similarity={decision.similarity_score:.3f}"
        if decision.route == FaceReviewRoute.ACCEPT:
            attempt = scheduling_service.review_attendance_attempt(
                attempt.id,
                decision_status=AttendanceDecisionStatus.ACCEPTED,
                decided_by=CV_ACTOR_ID,
                review_reason=f"auto-accepted {score}",
            )
        elif decision.route == FaceReviewRoute.REJECT:
            attempt = scheduling_service.review_attendance_attempt(
                attempt.id,
                decision_status=AttendanceDecisionStatus.REJECTED,
                decided_by=CV_ACTOR_ID,
                review_reason=f"auto-rejected {score}",
            )
        else:
            reason = "; ".join((f"needs human review ({score})", *decision.notes))
            attempt = scheduling_service.flag_attendance_attempt(attempt.id, review_reason=reason)
        return attempt, result

    def get_match_result(self, attempt_id: str) -> PersistedAttendanceMatchResult:
        result = self.repository.get_match_result_for_attempt(attempt_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="attendance match result not found")
        return result

    @staticmethod
    def _decode_media(media_base64: str) -> bytes:
        try:
            data = base64.b64decode(media_base64, validate=True)
        except Exception as exc:
            raise ApiError(status.HTTP_422_UNPROCESSABLE_CONTENT, "media_base64 is invalid", code="invalid_media") from exc
        if len(data) > MAX_MEDIA_BYTES:
            raise ApiError(status.HTTP_413_CONTENT_TOO_LARGE, "image is larger than 5 MB", code="media_too_large")
        return data

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:8]}"
