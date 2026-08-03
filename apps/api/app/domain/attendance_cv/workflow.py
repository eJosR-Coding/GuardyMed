from __future__ import annotations

import base64
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status

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
        if scheduling_service.repository.get_attendance_enrollment_by_worker(worker_id) is None:
            scheduling_service.create_attendance_enrollment(worker_id=worker_id, created_by=created_by)

        media_bytes = self._decode_media(media_base64)
        persisted = PersistedFaceEnrollment(
            id=self._new_id("fen"),
            worker_id=worker_id,
            status="active",
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
        )
        self.repository.create_face_enrollment(persisted)
        template_seed = self.cv_service.create_enrollment_template(worker_id=worker_id, media_bytes=media_bytes)
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
        return persisted, template

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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="worker can only submit attendance for own assignments")

        template = self.repository.get_latest_template_for_worker(worker_id)
        if template is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="face enrollment not found for worker")

        media_bytes = self._decode_media(media_base64)
        attempt = scheduling_service.create_attendance_attempt(
            worker_id=worker_id,
            assignment_id=assignment_id,
            attempt_type=attempt_type,
            evidence_ref="cv://inline-capture",
        )
        decision = self.cv_service.verify_attempt(
            worker_id=worker_id,
            assignment_id=assignment_id,
            enrollment_template=template,
            media_bytes=media_bytes,
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

        if decision.route == FaceReviewRoute.ACCEPT:
            attempt = scheduling_service.review_attendance_attempt(
                attempt.id,
                decision_status=AttendanceDecisionStatus.ACCEPTED,
                decided_by="system_cv",
                review_reason=f"auto-accepted similarity={decision.similarity_score:.4f}",
            )
        elif decision.route == FaceReviewRoute.REJECT:
            attempt = scheduling_service.review_attendance_attempt(
                attempt.id,
                decision_status=AttendanceDecisionStatus.REJECTED,
                decided_by="system_cv",
                review_reason=f"auto-rejected similarity={decision.similarity_score:.4f}",
            )

        return attempt, result

    def get_match_result(self, attempt_id: str) -> PersistedAttendanceMatchResult:
        result = self.repository.get_match_result_for_attempt(attempt_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="attendance match result not found")
        return result

    @staticmethod
    def _decode_media(media_base64: str) -> bytes:
        try:
            return base64.b64decode(media_base64, validate=True)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="media_base64 is invalid") from exc

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:8]}"
