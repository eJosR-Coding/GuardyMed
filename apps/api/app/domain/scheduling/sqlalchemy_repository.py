from __future__ import annotations

import json

from sqlalchemy import select

from apps.api.app.domain.scheduling.entities import (
    ApprovalDecision,
    ApprovalDecisionType,
    ApprovalTargetType,
    AssignmentType,
    AttendanceAttempt,
    AttendanceAttemptType,
    AttendanceDecisionStatus,
    AttendanceEnrollment,
    AttendanceEnrollmentStatus,
    AuditEvent,
    ChangeRequest,
    ChangeRequestStatus,
    ChangeRequestType,
    Department,
    ExportJob,
    ExportType,
    SchedulePeriod,
    SchedulePeriodStatus,
    ShiftAssignment,
    Worker,
)
from apps.api.app.infra.db import (
    ApprovalDecisionRow,
    AttendanceAttemptRow,
    AttendanceEnrollmentRow,
    AuditEventRow,
    ChangeRequestRow,
    DepartmentRow,
    ExportJobRow,
    SchedulePeriodRow,
    ShiftAssignmentRow,
    WorkerRow,
    session_scope,
)


class SQLAlchemySchedulingRepository:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def create_department(self, department: Department) -> Department:
        row = DepartmentRow(id=department.id, name=department.name, code=department.code)
        with session_scope(self.session_factory) as session:
            session.add(row)
        return department

    def get_department(self, department_id: str) -> Department | None:
        with session_scope(self.session_factory) as session:
            row = session.get(DepartmentRow, department_id)
            return None if row is None else Department(id=row.id, name=row.name, code=row.code)

    def list_departments(self) -> list[Department]:
        with session_scope(self.session_factory) as session:
            rows = session.scalars(select(DepartmentRow).order_by(DepartmentRow.name)).all()
            return [Department(id=row.id, name=row.name, code=row.code) for row in rows]

    def create_worker(self, worker: Worker) -> Worker:
        row = WorkerRow(
            id=worker.id,
            full_name=worker.full_name,
            document_id=worker.document_id,
            worker_type=worker.worker_type,
            department_id=worker.department_id,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return worker

    def get_worker(self, worker_id: str) -> Worker | None:
        with session_scope(self.session_factory) as session:
            row = session.get(WorkerRow, worker_id)
            return None if row is None else self._worker_from_row(row)

    def list_workers(self, department_id: str | None = None) -> list[Worker]:
        statement = select(WorkerRow).order_by(WorkerRow.full_name)
        if department_id is not None:
            statement = statement.where(WorkerRow.department_id == department_id)
        with session_scope(self.session_factory) as session:
            rows = session.scalars(statement).all()
            return [self._worker_from_row(row) for row in rows]

    def create_period(self, period: SchedulePeriod) -> SchedulePeriod:
        row = SchedulePeriodRow(
            id=period.id,
            year=period.year,
            month=period.month,
            department_id=period.department_id,
            created_by=period.created_by,
            status=period.status,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return period

    def get_period(self, period_id: str) -> SchedulePeriod | None:
        with session_scope(self.session_factory) as session:
            row = session.get(SchedulePeriodRow, period_id)
            return None if row is None else self._period_from_row(row)

    def list_periods(self, department_id: str | None = None) -> list[SchedulePeriod]:
        statement = select(SchedulePeriodRow).order_by(SchedulePeriodRow.year.desc(), SchedulePeriodRow.month.desc())
        if department_id is not None:
            statement = statement.where(SchedulePeriodRow.department_id == department_id)
        with session_scope(self.session_factory) as session:
            rows = session.scalars(statement).all()
            return [self._period_from_row(row) for row in rows]

    def update_period(self, period: SchedulePeriod) -> SchedulePeriod:
        with session_scope(self.session_factory) as session:
            row = session.get(SchedulePeriodRow, period.id)
            if row is None:
                raise KeyError(period.id)
            row.year = period.year
            row.month = period.month
            row.department_id = period.department_id
            row.created_by = period.created_by
            row.status = period.status
        return period

    def create_assignment(self, assignment: ShiftAssignment) -> ShiftAssignment:
        row = ShiftAssignmentRow(
            id=assignment.id,
            schedule_period_id=assignment.schedule_period_id,
            worker_id=assignment.worker_id,
            assignment_type=assignment.assignment_type,
            shift_date=assignment.shift_date,
            start_time=assignment.start_time,
            end_time=assignment.end_time,
            notes=assignment.notes,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return assignment

    def get_assignment(self, assignment_id: str) -> ShiftAssignment | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ShiftAssignmentRow, assignment_id)
            return None if row is None else self._assignment_from_row(row)

    def update_assignment(self, assignment: ShiftAssignment) -> ShiftAssignment:
        with session_scope(self.session_factory) as session:
            row = session.get(ShiftAssignmentRow, assignment.id)
            if row is None:
                raise KeyError(assignment.id)
            row.start_time = assignment.start_time
            row.end_time = assignment.end_time
            row.notes = assignment.notes
        return assignment

    def list_assignments_for_period(self, period_id: str) -> list[ShiftAssignment]:
        with session_scope(self.session_factory) as session:
            rows = session.scalars(select(ShiftAssignmentRow).where(ShiftAssignmentRow.schedule_period_id == period_id)).all()
            return [self._assignment_from_row(row) for row in rows]

    def list_assignments_for_worker(self, worker_id: str) -> list[ShiftAssignment]:
        with session_scope(self.session_factory) as session:
            rows = session.scalars(
                select(ShiftAssignmentRow)
                .where(ShiftAssignmentRow.worker_id == worker_id)
                .order_by(ShiftAssignmentRow.shift_date, ShiftAssignmentRow.start_time)
            ).all()
            return [self._assignment_from_row(row) for row in rows]

    def create_change_request(self, change_request: ChangeRequest) -> ChangeRequest:
        row = ChangeRequestRow(
            id=change_request.id,
            assignment_id=change_request.assignment_id,
            requested_by=change_request.requested_by,
            request_type=change_request.request_type,
            reason=change_request.reason,
            status=change_request.status,
            replacement_worker_id=change_request.replacement_worker_id,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return change_request

    def get_change_request(self, request_id: str) -> ChangeRequest | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ChangeRequestRow, request_id)
            return None if row is None else self._change_request_from_row(row)

    def list_change_requests(self, requested_by: str | None = None) -> list[ChangeRequest]:
        statement = select(ChangeRequestRow).order_by(ChangeRequestRow.id.desc())
        if requested_by is not None:
            statement = statement.where(ChangeRequestRow.requested_by == requested_by)
        with session_scope(self.session_factory) as session:
            rows = session.scalars(statement).all()
            return [self._change_request_from_row(row) for row in rows]

    def update_change_request(self, change_request: ChangeRequest) -> ChangeRequest:
        with session_scope(self.session_factory) as session:
            row = session.get(ChangeRequestRow, change_request.id)
            if row is None:
                raise KeyError(change_request.id)
            row.status = change_request.status
            row.reason = change_request.reason
            row.replacement_worker_id = change_request.replacement_worker_id
        return change_request

    def create_approval_decision(self, approval_decision: ApprovalDecision) -> ApprovalDecision:
        row = ApprovalDecisionRow(
            id=approval_decision.id,
            target_type=approval_decision.target_type,
            target_id=approval_decision.target_id,
            decision=approval_decision.decision,
            decided_by=approval_decision.decided_by,
            comment=approval_decision.comment,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return approval_decision

    def create_audit_event(self, audit_event: AuditEvent) -> AuditEvent:
        row = AuditEventRow(
            id=audit_event.id,
            actor_id=audit_event.actor_id,
            entity_type=audit_event.entity_type,
            entity_id=audit_event.entity_id,
            action=audit_event.action,
            payload=json.dumps(audit_event.payload),
            created_at=audit_event.created_at,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return audit_event

    def list_audit_events(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> list[AuditEvent]:
        statement = select(AuditEventRow).order_by(AuditEventRow.created_at)
        if entity_type is not None:
            statement = statement.where(AuditEventRow.entity_type == entity_type)
        if entity_id is not None:
            statement = statement.where(AuditEventRow.entity_id == entity_id)
        with session_scope(self.session_factory) as session:
            rows = session.scalars(statement).all()
            return [self._audit_event_from_row(row) for row in rows]

    def create_export(self, export_job: ExportJob) -> ExportJob:
        row = ExportJobRow(
            id=export_job.id,
            schedule_period_id=export_job.schedule_period_id,
            export_type=export_job.export_type,
            created_by=export_job.created_by,
            content=export_job.content,
            created_at=export_job.created_at,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return export_job

    def get_export(self, export_id: str) -> ExportJob | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ExportJobRow, export_id)
            return None if row is None else self._export_from_row(row)

    def list_exports_for_period(self, period_id: str) -> list[ExportJob]:
        with session_scope(self.session_factory) as session:
            rows = session.scalars(
                select(ExportJobRow).where(ExportJobRow.schedule_period_id == period_id).order_by(ExportJobRow.created_at)
            ).all()
            return [self._export_from_row(row) for row in rows]

    def create_attendance_enrollment(self, enrollment: AttendanceEnrollment) -> AttendanceEnrollment:
        row = AttendanceEnrollmentRow(
            id=enrollment.id,
            worker_id=enrollment.worker_id,
            status=enrollment.status,
            created_by=enrollment.created_by,
            created_at=enrollment.created_at,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return enrollment

    def get_attendance_enrollment_by_worker(self, worker_id: str) -> AttendanceEnrollment | None:
        with session_scope(self.session_factory) as session:
            row = session.scalar(select(AttendanceEnrollmentRow).where(AttendanceEnrollmentRow.worker_id == worker_id))
            return None if row is None else self._attendance_enrollment_from_row(row)

    def list_attendance_enrollments(self, worker_id: str | None = None) -> list[AttendanceEnrollment]:
        statement = select(AttendanceEnrollmentRow).order_by(AttendanceEnrollmentRow.created_at)
        if worker_id is not None:
            statement = statement.where(AttendanceEnrollmentRow.worker_id == worker_id)
        with session_scope(self.session_factory) as session:
            rows = session.scalars(statement).all()
            return [self._attendance_enrollment_from_row(row) for row in rows]

    def update_attendance_enrollment(self, enrollment: AttendanceEnrollment) -> AttendanceEnrollment:
        with session_scope(self.session_factory) as session:
            row = session.get(AttendanceEnrollmentRow, enrollment.id)
            if row is None:
                raise KeyError(enrollment.id)
            row.status = enrollment.status
            row.created_by = enrollment.created_by
            row.created_at = enrollment.created_at
        return enrollment

    def create_attendance_attempt(self, attempt: AttendanceAttempt) -> AttendanceAttempt:
        row = AttendanceAttemptRow(
            id=attempt.id,
            worker_id=attempt.worker_id,
            assignment_id=attempt.assignment_id,
            attempt_type=attempt.attempt_type,
            evidence_ref=attempt.evidence_ref,
            attempted_at=attempt.attempted_at,
            decision_status=attempt.decision_status,
            review_reason=attempt.review_reason,
            decided_by=attempt.decided_by,
            decided_at=attempt.decided_at,
        )
        with session_scope(self.session_factory) as session:
            session.add(row)
        return attempt

    def get_attendance_attempt(self, attempt_id: str) -> AttendanceAttempt | None:
        with session_scope(self.session_factory) as session:
            row = session.get(AttendanceAttemptRow, attempt_id)
            return None if row is None else self._attendance_attempt_from_row(row)

    def list_attendance_attempts(
        self,
        *,
        worker_id: str | None = None,
        pending_only: bool = False,
    ) -> list[AttendanceAttempt]:
        statement = select(AttendanceAttemptRow).order_by(AttendanceAttemptRow.attempted_at.desc())
        if worker_id is not None:
            statement = statement.where(AttendanceAttemptRow.worker_id == worker_id)
        if pending_only:
            statement = statement.where(AttendanceAttemptRow.decision_status == AttendanceDecisionStatus.PENDING)
        with session_scope(self.session_factory) as session:
            rows = session.scalars(statement).all()
            return [self._attendance_attempt_from_row(row) for row in rows]

    def update_attendance_attempt(self, attempt: AttendanceAttempt) -> AttendanceAttempt:
        with session_scope(self.session_factory) as session:
            row = session.get(AttendanceAttemptRow, attempt.id)
            if row is None:
                raise KeyError(attempt.id)
            row.evidence_ref = attempt.evidence_ref
            row.decision_status = attempt.decision_status
            row.review_reason = attempt.review_reason
            row.decided_by = attempt.decided_by
            row.decided_at = attempt.decided_at
        return attempt

    @staticmethod
    def _worker_from_row(row: WorkerRow) -> Worker:
        return Worker(
            id=row.id,
            full_name=row.full_name,
            document_id=row.document_id,
            worker_type=row.worker_type,
            department_id=row.department_id,
        )

    @staticmethod
    def _period_from_row(row: SchedulePeriodRow) -> SchedulePeriod:
        return SchedulePeriod(
            id=row.id,
            year=row.year,
            month=row.month,
            department_id=row.department_id,
            created_by=row.created_by,
            status=SchedulePeriodStatus(row.status),
        )

    @staticmethod
    def _assignment_from_row(row: ShiftAssignmentRow) -> ShiftAssignment:
        return ShiftAssignment(
            id=row.id,
            schedule_period_id=row.schedule_period_id,
            worker_id=row.worker_id,
            assignment_type=AssignmentType(row.assignment_type),
            shift_date=row.shift_date,
            start_time=row.start_time,
            end_time=row.end_time,
            notes=row.notes,
        )

    @staticmethod
    def _change_request_from_row(row: ChangeRequestRow) -> ChangeRequest:
        return ChangeRequest(
            id=row.id,
            assignment_id=row.assignment_id,
            requested_by=row.requested_by,
            request_type=ChangeRequestType(row.request_type),
            reason=row.reason,
            status=ChangeRequestStatus(row.status),
            replacement_worker_id=row.replacement_worker_id,
        )

    @staticmethod
    def _audit_event_from_row(row: AuditEventRow) -> AuditEvent:
        return AuditEvent(
            id=row.id,
            actor_id=row.actor_id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            action=row.action,
            payload=json.loads(row.payload),
            created_at=row.created_at,
        )

    @staticmethod
    def _export_from_row(row: ExportJobRow) -> ExportJob:
        return ExportJob(
            id=row.id,
            schedule_period_id=row.schedule_period_id,
            export_type=ExportType(row.export_type),
            created_by=row.created_by,
            content=row.content,
            created_at=row.created_at,
        )

    @staticmethod
    def _attendance_enrollment_from_row(row: AttendanceEnrollmentRow) -> AttendanceEnrollment:
        return AttendanceEnrollment(
            id=row.id,
            worker_id=row.worker_id,
            status=AttendanceEnrollmentStatus(row.status),
            created_by=row.created_by,
            created_at=row.created_at,
        )

    @staticmethod
    def _attendance_attempt_from_row(row: AttendanceAttemptRow) -> AttendanceAttempt:
        return AttendanceAttempt(
            id=row.id,
            worker_id=row.worker_id,
            assignment_id=row.assignment_id,
            attempt_type=AttendanceAttemptType(row.attempt_type),
            evidence_ref=row.evidence_ref,
            attempted_at=row.attempted_at,
            decision_status=AttendanceDecisionStatus(row.decision_status),
            review_reason=row.review_reason,
            decided_by=row.decided_by,
            decided_at=row.decided_at,
        )
