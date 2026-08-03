from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select

from apps.api.app.domain.attendance_cv.entities import (
    FaceEnrollmentTemplate,
    FaceReviewRoute,
    FaceVector,
    PersistedAttendanceMatchResult,
    PersistedFaceEnrollment,
)
from apps.api.app.infra.db import AttendanceMatchResultRow, FaceEnrollmentRow, FaceTemplateRow, session_scope


class SQLAlchemyAttendanceCVRepository:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def create_face_enrollment(self, enrollment: PersistedFaceEnrollment) -> PersistedFaceEnrollment:
        row = FaceEnrollmentRow(
            id=enrollment.id,
            worker_id=enrollment.worker_id,
            status=enrollment.status,
            created_by=enrollment.created_by,
            created_at=enrollment.created_at,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return enrollment

    def create_face_template(self, template: FaceEnrollmentTemplate) -> FaceEnrollmentTemplate:
        row = FaceTemplateRow(
            id=template.id,
            enrollment_id=template.enrollment_id,
            embedding_json=json.dumps(list(template.embedding.values)),
            quality_score=template.quality_score,
            detector_name=template.detector_name,
            model_name=template.model_name,
            created_at=template.created_at,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return template

    def get_latest_template_for_worker(self, worker_id: str) -> FaceEnrollmentTemplate | None:
        statement = (
            select(FaceTemplateRow, FaceEnrollmentRow)
            .join(FaceEnrollmentRow, FaceTemplateRow.enrollment_id == FaceEnrollmentRow.id)
            .where(FaceEnrollmentRow.worker_id == worker_id)
            .order_by(FaceTemplateRow.created_at.desc())
        )
        with session_scope(self.session_factory) as session:
            row = session.execute(statement).first()
            if row is None:
                return None
            template_row, enrollment_row = row
            return FaceEnrollmentTemplate(
                id=template_row.id,
                enrollment_id=template_row.enrollment_id,
                worker_id=enrollment_row.worker_id,
                embedding=FaceVector(values=tuple(float(value) for value in json.loads(template_row.embedding_json))),
                quality_score=template_row.quality_score,
                detector_name=template_row.detector_name,
                model_name=template_row.model_name,
                created_at=template_row.created_at,
            )

    def list_face_enrollments(self) -> list[PersistedFaceEnrollment]:
        with session_scope(self.session_factory) as session:
            rows = session.scalars(select(FaceEnrollmentRow).order_by(FaceEnrollmentRow.created_at.desc())).all()
            return [
                PersistedFaceEnrollment(
                    id=row.id,
                    worker_id=row.worker_id,
                    status=row.status,
                    created_by=row.created_by,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    def create_match_result(self, result: PersistedAttendanceMatchResult) -> PersistedAttendanceMatchResult:
        row = AttendanceMatchResultRow(
            id=result.id,
            attempt_id=result.attempt_id,
            enrollment_id=result.enrollment_id,
            similarity_score=result.similarity_score,
            route=result.route,
            threshold_accept=result.threshold_accept,
            threshold_review=result.threshold_review,
            detector_name=result.detector_name,
            model_name=result.model_name,
            processed_at=result.processed_at,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return result

    def get_match_result_for_attempt(self, attempt_id: str) -> PersistedAttendanceMatchResult | None:
        with session_scope(self.session_factory) as session:
            row = session.scalar(select(AttendanceMatchResultRow).where(AttendanceMatchResultRow.attempt_id == attempt_id))
            if row is None:
                return None
            return PersistedAttendanceMatchResult(
                id=row.id,
                attempt_id=row.attempt_id,
                enrollment_id=row.enrollment_id,
                similarity_score=row.similarity_score,
                route=FaceReviewRoute(row.route),
                threshold_accept=row.threshold_accept,
                threshold_review=row.threshold_review,
                detector_name=row.detector_name,
                model_name=row.model_name,
                processed_at=row.processed_at,
            )
