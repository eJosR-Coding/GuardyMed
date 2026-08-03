from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import uuid4

from fastapi import HTTPException, status

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
    ScheduleCalendar,
    SchedulePeriod,
    SchedulePeriodStatus,
    ShiftAssignment,
    Worker,
)
from apps.api.app.domain.scheduling.repository import InMemorySchedulingRepository
from apps.api.app.domain.scheduling.rules import (
    SYSTEM_ACTOR_ID,
    AuditAction,
    build_export_lines,
    ensure_no_assignment_overlap,
    ensure_unique_department_code,
    ensure_unique_schedule_period,
    ensure_unique_worker_document,
    next_change_request_status_from_decision,
    next_schedule_period_status_from_decision,
    require_pending_change_request,
    validate_schedule_period_editable,
    validate_schedule_period_status_transition,
    validate_change_request_status_transition,
    validate_exportable_period,
    validate_month,
    validate_time_window,
    require_active_attendance_enrollment,
    require_pending_attendance_attempt,
)


class SchedulingService:
    def __init__(self, repository: InMemorySchedulingRepository) -> None:
        self.repository = repository

    def create_department(self, *, name: str, code: str) -> Department:
        ensure_unique_department_code({item.code.casefold() for item in self.repository.list_departments()}, code.casefold())
        department = Department(id=self._new_id("dep"), name=name, code=code)
        created = self.repository.create_department(department)
        self._record_event(
            actor_id=SYSTEM_ACTOR_ID,
            entity_type="department",
            entity_id=created.id,
            action=AuditAction.DEPARTMENT_CREATED,
            payload={"name": created.name, "code": created.code},
        )
        return created

    def list_departments(self) -> list[Department]:
        return self.repository.list_departments()

    def create_worker(
        self,
        *,
        full_name: str,
        document_id: str,
        worker_type: str,
        department_id: str,
    ) -> Worker:
        self._require_department(department_id)
        ensure_unique_worker_document(
            {item.document_id.casefold() for item in self.repository.list_workers()},
            document_id.casefold(),
        )
        worker = Worker(
            id=self._new_id("wrk"),
            full_name=full_name,
            document_id=document_id,
            worker_type=worker_type,
            department_id=department_id,
        )
        created = self.repository.create_worker(worker)
        self._record_event(
            actor_id=SYSTEM_ACTOR_ID,
            entity_type="worker",
            entity_id=created.id,
            action=AuditAction.WORKER_CREATED,
            payload={"department_id": created.department_id, "worker_type": created.worker_type},
        )
        return created

    def list_workers(self, *, department_id: str | None = None) -> list[Worker]:
        if department_id is not None:
            self._require_department(department_id)
        return self.repository.list_workers(department_id=department_id)

    def create_period(
        self,
        *,
        year: int,
        month: int,
        department_id: str,
        created_by: str | None,
    ) -> SchedulePeriod:
        self._require_department(department_id)
        validate_month(month)
        ensure_unique_schedule_period(
            {(item.department_id, item.year, item.month) for item in self.repository.list_periods()},
            department_id,
            year,
            month,
        )
        period = SchedulePeriod(
            id=self._new_id("sp"),
            year=year,
            month=month,
            department_id=department_id,
            created_by=created_by,
        )
        created = self.repository.create_period(period)
        self._record_event(
            actor_id=created_by or SYSTEM_ACTOR_ID,
            entity_type="schedule_period",
            entity_id=created.id,
            action=AuditAction.SCHEDULE_PERIOD_CREATED,
            payload={"year": created.year, "month": created.month, "department_id": created.department_id},
        )
        return created

    def get_period(self, period_id: str) -> SchedulePeriod:
        period = self.repository.get_period(period_id)
        if period is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="schedule period not found")
        return period

    def list_periods(self, *, department_id: str | None = None) -> list[SchedulePeriod]:
        if department_id is not None:
            self._require_department(department_id)
        return self.repository.list_periods(department_id=department_id)

    def update_period_status(self, period_id: str, *, status_value: SchedulePeriodStatus) -> SchedulePeriod:
        period = self.get_period(period_id)
        validate_schedule_period_status_transition(current_status=period.status, next_status=status_value)
        period.status = status_value
        updated = self.repository.update_period(period)
        self._record_event(
            actor_id=SYSTEM_ACTOR_ID,
            entity_type="schedule_period",
            entity_id=updated.id,
            action=AuditAction.SCHEDULE_PERIOD_STATUS_UPDATED,
            payload={"status": updated.status},
        )
        return updated

    def create_assignment(
        self,
        *,
        period_id: str,
        worker_id: str,
        assignment_type: AssignmentType,
        shift_date: date,
        start_time: time,
        end_time: time,
        notes: str | None,
    ) -> ShiftAssignment:
        period = self.get_period(period_id)
        worker = self._require_worker(worker_id)
        if worker.department_id != period.department_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="worker does not belong to the schedule department")
        validate_schedule_period_editable(period.status)
        validate_time_window(start_time=start_time, end_time=end_time)
        overlaps = any(
            item.shift_date == shift_date and start_time < item.end_time and end_time > item.start_time
            for item in self.repository.list_assignments_for_worker(worker_id)
        )
        ensure_no_assignment_overlap(overlaps)
        assignment = ShiftAssignment(
            id=self._new_id("asg"),
            schedule_period_id=period_id,
            worker_id=worker_id,
            assignment_type=assignment_type,
            shift_date=shift_date,
            start_time=start_time,
            end_time=end_time,
            notes=notes,
        )
        created = self.repository.create_assignment(assignment)
        self._record_event(
            actor_id=SYSTEM_ACTOR_ID,
            entity_type="assignment",
            entity_id=created.id,
            action=AuditAction.ASSIGNMENT_CREATED,
            payload={"schedule_period_id": created.schedule_period_id, "worker_id": created.worker_id},
        )
        return created

    def update_assignment(
        self,
        assignment_id: str,
        *,
        start_time: time,
        end_time: time,
        notes: str | None,
    ) -> ShiftAssignment:
        assignment = self.repository.get_assignment(assignment_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assignment not found")
        period = self.get_period(assignment.schedule_period_id)
        validate_schedule_period_editable(period.status)
        validate_time_window(start_time=start_time, end_time=end_time)
        overlaps = any(
            item.id != assignment.id
            and item.shift_date == assignment.shift_date
            and start_time < item.end_time
            and end_time > item.start_time
            for item in self.repository.list_assignments_for_worker(assignment.worker_id)
        )
        ensure_no_assignment_overlap(overlaps)
        assignment.start_time = start_time
        assignment.end_time = end_time
        assignment.notes = notes
        updated = self.repository.update_assignment(assignment)
        self._record_event(
            actor_id=SYSTEM_ACTOR_ID,
            entity_type="assignment",
            entity_id=updated.id,
            action=AuditAction.ASSIGNMENT_UPDATED,
            payload={"start_time": str(updated.start_time), "end_time": str(updated.end_time), "notes": updated.notes},
        )
        return updated

    def get_assignment(self, assignment_id: str) -> ShiftAssignment:
        assignment = self.repository.get_assignment(assignment_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assignment not found")
        return assignment

    def get_calendar(self, period_id: str) -> ScheduleCalendar:
        period = self.get_period(period_id)
        assignments = self.repository.list_assignments_for_period(period_id)
        assignments.sort(key=lambda item: (item.shift_date, item.start_time, item.worker_id))
        return ScheduleCalendar(period=period, assignments=assignments)

    def list_assignments_for_worker(self, worker_id: str) -> list[ShiftAssignment]:
        self._require_worker(worker_id)
        return self.repository.list_assignments_for_worker(worker_id)

    def create_change_request(
        self,
        *,
        assignment_id: str,
        requested_by: str,
        request_type: ChangeRequestType,
        reason: str,
        replacement_worker_id: str | None,
    ) -> ChangeRequest:
        assignment = self.get_assignment(assignment_id)
        if not reason.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="reason is required")
        if assignment.worker_id != requested_by:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="worker can only request changes for own assignments")
        if replacement_worker_id is not None:
            self._require_worker(replacement_worker_id)
        change_request = ChangeRequest(
            id=self._new_id("cr"),
            assignment_id=assignment.id,
            requested_by=requested_by,
            request_type=request_type,
            reason=reason.strip(),
            replacement_worker_id=replacement_worker_id,
        )
        created = self.repository.create_change_request(change_request)
        self._record_event(
            actor_id=created.requested_by,
            entity_type="change_request",
            entity_id=created.id,
            action=AuditAction.CHANGE_REQUEST_CREATED,
            payload={"assignment_id": created.assignment_id, "request_type": created.request_type},
        )
        return created

    def get_change_request(self, request_id: str) -> ChangeRequest:
        change_request = self.repository.get_change_request(request_id)
        if change_request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="change request not found")
        return change_request

    def list_change_requests(self, *, requested_by: str | None = None) -> list[ChangeRequest]:
        if requested_by is not None:
            self._require_worker(requested_by)
        return self.repository.list_change_requests(requested_by=requested_by)

    def update_change_request_status(
        self,
        request_id: str,
        *,
        status_value: ChangeRequestStatus,
    ) -> ChangeRequest:
        change_request = self.get_change_request(request_id)
        require_pending_change_request(change_request.status)
        validate_change_request_status_transition(status_value)
        change_request.status = status_value
        updated = self.repository.update_change_request(change_request)
        self._record_event(
            actor_id=updated.requested_by,
            entity_type="change_request",
            entity_id=updated.id,
            action=AuditAction.CHANGE_REQUEST_STATUS_UPDATED,
            payload={"status": updated.status},
        )
        return updated

    def create_approval_decision(
        self,
        *,
        target_type: ApprovalTargetType,
        target_id: str,
        decision: ApprovalDecisionType,
        decided_by: str,
        comment: str | None,
    ) -> ApprovalDecision:
        if not decided_by.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="decided_by is required")

        if target_type == ApprovalTargetType.SCHEDULE_PERIOD:
            self._apply_schedule_period_decision(target_id, decision)
        elif target_type == ApprovalTargetType.CHANGE_REQUEST:
            self._apply_change_request_decision(target_id, decision)
        else:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid approval target type")

        approval_decision = ApprovalDecision(
            id=self._new_id("ad"),
            target_type=target_type,
            target_id=target_id,
            decision=decision,
            decided_by=decided_by.strip(),
            comment=comment.strip() if comment else None,
        )
        created = self.repository.create_approval_decision(approval_decision)
        self._record_event(
            actor_id=created.decided_by,
            entity_type="approval_decision",
            entity_id=created.id,
            action=AuditAction.APPROVAL_DECISION_CREATED,
            payload={"target_type": created.target_type, "target_id": created.target_id, "decision": created.decision},
        )
        return created

    def list_review_queue(self) -> dict[str, list[object]]:
        periods = [period for period in self.repository.list_periods() if period.status == SchedulePeriodStatus.IN_REVIEW]
        requests = [
            change_request for change_request in self.repository.list_change_requests() if change_request.status == ChangeRequestStatus.PENDING
        ]
        periods.sort(key=lambda item: (item.year, item.month, item.id))
        requests.sort(key=lambda item: item.id)
        return {"schedule_periods": periods, "change_requests": requests}

    def list_audit_events(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> list[AuditEvent]:
        return self.repository.list_audit_events(entity_type=entity_type, entity_id=entity_id)

    def create_export(
        self,
        *,
        period_id: str,
        export_type: ExportType,
        created_by: str,
    ) -> ExportJob:
        period = self.get_period(period_id)
        validate_exportable_period(period.status)
        if not created_by.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="created_by is required")

        assignments = self.repository.list_assignments_for_period(period_id)
        content = self._build_export_content(period=period, assignments=assignments, export_type=export_type)
        export_job = ExportJob(
            id=self._new_id("exp"),
            schedule_period_id=period.id,
            export_type=export_type,
            created_by=created_by.strip(),
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        created = self.repository.create_export(export_job)
        self._record_event(
            actor_id=created.created_by,
            entity_type="export_job",
            entity_id=created.id,
            action=AuditAction.EXPORT_CREATED,
            payload={"schedule_period_id": created.schedule_period_id, "export_type": created.export_type},
        )
        return created

    def get_export(self, export_id: str) -> ExportJob:
        export_job = self.repository.get_export(export_id)
        if export_job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="export not found")
        return export_job

    def list_exports_for_period(self, period_id: str) -> list[ExportJob]:
        self.get_period(period_id)
        exports = self.repository.list_exports_for_period(period_id)
        exports.sort(key=lambda item: item.created_at)
        return exports

    def seed_demo_data(self) -> dict[str, int | bool]:
        if self.repository.list_departments():
            return {
                "seeded": False,
                "departments": len(self.repository.list_departments()),
                "workers": len(self.repository.list_workers()),
                "periods": len(self.repository.list_periods()),
                "assignments": sum(len(self.repository.list_assignments_for_period(item.id)) for item in self.repository.list_periods()),
                "change_requests": len(self.repository.list_change_requests()),
            }

        department = self.create_department(name="Emergency", code="ER")
        worker_1 = self.create_worker(
            full_name="Ana Ruiz",
            document_id="10010010",
            worker_type="Nurse",
            department_id=department.id,
        )
        worker_2 = self.create_worker(
            full_name="Luis Torres",
            document_id="20020020",
            worker_type="Doctor",
            department_id=department.id,
        )
        worker_3 = self.create_worker(
            full_name="Marta Vega",
            document_id="30030030",
            worker_type="Nurse",
            department_id=department.id,
        )
        period = self.create_period(year=2026, month=8, department_id=department.id, created_by="coord_demo")
        assignment_1 = self.create_assignment(
            period_id=period.id,
            worker_id=worker_1.id,
            assignment_type=AssignmentType.GUARD_SHIFT,
            shift_date=date(2026, 8, 4),
            start_time=time(8, 0),
            end_time=time(20, 0),
            notes="Emergency daytime coverage",
        )
        self.create_assignment(
            period_id=period.id,
            worker_id=worker_2.id,
            assignment_type=AssignmentType.SHIFT_LEAD,
            shift_date=date(2026, 8, 5),
            start_time=time(20, 0),
            end_time=time(23, 59),
            notes="Night shift lead",
        )
        self.create_assignment(
            period_id=period.id,
            worker_id=worker_3.id,
            assignment_type=AssignmentType.ON_CALL,
            shift_date=date(2026, 8, 6),
            start_time=time(8, 0),
            end_time=time(18, 0),
            notes="Backup coverage",
        )
        self.create_change_request(
            assignment_id=assignment_1.id,
            requested_by=worker_1.id,
            request_type=ChangeRequestType.ADJUSTMENT,
            reason="Medical appointment overlap",
            replacement_worker_id=worker_3.id,
        )
        self.create_attendance_enrollment(worker_id=worker_1.id, created_by="coord_demo")
        self.create_attendance_attempt(
            worker_id=worker_1.id,
            assignment_id=assignment_1.id,
            attempt_type=AttendanceAttemptType.CHECK_IN,
            evidence_ref="manual://demo-check-in",
        )

        return {
            "seeded": True,
            "departments": 1,
            "workers": 3,
            "periods": 1,
            "assignments": 3,
            "change_requests": 1,
        }

    def create_attendance_enrollment(self, *, worker_id: str, created_by: str) -> AttendanceEnrollment:
        self._require_worker(worker_id)
        existing = self.repository.get_attendance_enrollment_by_worker(worker_id)
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="attendance enrollment already exists for worker")
        enrollment = AttendanceEnrollment(
            id=self._new_id("aen"),
            worker_id=worker_id,
            status=AttendanceEnrollmentStatus.ACTIVE,
            created_by=created_by.strip() or SYSTEM_ACTOR_ID,
            created_at=datetime.now(timezone.utc),
        )
        created = self.repository.create_attendance_enrollment(enrollment)
        self._record_event(
            actor_id=created.created_by,
            entity_type="attendance_enrollment",
            entity_id=created.id,
            action=AuditAction.ATTENDANCE_ENROLLMENT_CREATED,
            payload={"worker_id": created.worker_id, "status": created.status},
        )
        return created

    def list_attendance_enrollments(self, *, worker_id: str | None = None) -> list[AttendanceEnrollment]:
        if worker_id is not None:
            self._require_worker(worker_id)
        return self.repository.list_attendance_enrollments(worker_id=worker_id)

    def create_attendance_attempt(
        self,
        *,
        worker_id: str,
        assignment_id: str,
        attempt_type: AttendanceAttemptType,
        evidence_ref: str | None,
    ) -> AttendanceAttempt:
        self._require_worker(worker_id)
        assignment = self.get_assignment(assignment_id)
        if assignment.worker_id != worker_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="worker can only submit attendance for own assignments")
        enrollment = self.repository.get_attendance_enrollment_by_worker(worker_id)
        require_active_attendance_enrollment(enrollment is not None and enrollment.status == AttendanceEnrollmentStatus.ACTIVE)
        attempt = AttendanceAttempt(
            id=self._new_id("aat"),
            worker_id=worker_id,
            assignment_id=assignment_id,
            attempt_type=attempt_type,
            evidence_ref=evidence_ref.strip() if evidence_ref else None,
            attempted_at=datetime.now(timezone.utc),
        )
        created = self.repository.create_attendance_attempt(attempt)
        self._record_event(
            actor_id=created.worker_id,
            entity_type="attendance_attempt",
            entity_id=created.id,
            action=AuditAction.ATTENDANCE_ATTEMPT_CREATED,
            payload={"assignment_id": created.assignment_id, "attempt_type": created.attempt_type},
        )
        return created

    def get_attendance_attempt(self, attempt_id: str) -> AttendanceAttempt:
        attempt = self.repository.get_attendance_attempt(attempt_id)
        if attempt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="attendance attempt not found")
        return attempt

    def list_attendance_attempts(
        self,
        *,
        worker_id: str | None = None,
        pending_only: bool = False,
    ) -> list[AttendanceAttempt]:
        if worker_id is not None:
            self._require_worker(worker_id)
        return self.repository.list_attendance_attempts(worker_id=worker_id, pending_only=pending_only)

    def review_attendance_attempt(
        self,
        attempt_id: str,
        *,
        decision_status: AttendanceDecisionStatus,
        decided_by: str,
        review_reason: str | None,
    ) -> AttendanceAttempt:
        attempt = self.get_attendance_attempt(attempt_id)
        require_pending_attendance_attempt(attempt.decision_status)
        if decision_status == AttendanceDecisionStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="decision status must be accepted or rejected")
        attempt.decision_status = decision_status
        attempt.decided_by = decided_by.strip()
        attempt.review_reason = review_reason.strip() if review_reason else None
        attempt.decided_at = datetime.now(timezone.utc)
        updated = self.repository.update_attendance_attempt(attempt)
        self._record_event(
            actor_id=updated.decided_by or SYSTEM_ACTOR_ID,
            entity_type="attendance_attempt",
            entity_id=updated.id,
            action=AuditAction.ATTENDANCE_ATTEMPT_REVIEWED,
            payload={"decision_status": updated.decision_status, "assignment_id": updated.assignment_id},
        )
        return updated

    def _require_department(self, department_id: str) -> Department:
        department = self.repository.get_department(department_id)
        if department is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="department not found")
        return department

    def _require_worker(self, worker_id: str) -> Worker:
        worker = self.repository.get_worker(worker_id)
        if worker is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="worker not found")
        return worker

    def _apply_schedule_period_decision(self, period_id: str, decision: ApprovalDecisionType) -> None:
        period = self.get_period(period_id)
        period.status = next_schedule_period_status_from_decision(
            current_status=period.status,
            decision=decision,
        )
        self.repository.update_period(period)

    def _apply_change_request_decision(self, request_id: str, decision: ApprovalDecisionType) -> None:
        change_request = self.get_change_request(request_id)
        change_request.status = next_change_request_status_from_decision(
            current_status=change_request.status,
            decision=decision,
        )
        self.repository.update_change_request(change_request)
        self._record_event(
            actor_id=SYSTEM_ACTOR_ID,
            entity_type="change_request",
            entity_id=change_request.id,
            action=AuditAction.CHANGE_REQUEST_REVIEWED,
            payload={"status": change_request.status},
        )

    def _record_event(
        self,
        *,
        actor_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        payload: dict[str, object],
    ) -> AuditEvent:
        event = AuditEvent(
            id=self._new_id("evt"),
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
        return self.repository.create_audit_event(event)

    def _build_export_content(
        self,
        *,
        period: SchedulePeriod,
        assignments: list[ShiftAssignment],
        export_type: ExportType,
    ) -> str:
        assignment_count = len(assignments)
        worker_count = len({item.worker_id for item in assignments})
        lines = build_export_lines(
            export_type=export_type,
            year=period.year,
            month=period.month,
            department_id=period.department_id,
            assignment_count=assignment_count,
            worker_count=worker_count,
        )
        return "\n".join(lines)

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:8]}"
