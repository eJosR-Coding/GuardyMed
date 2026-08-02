from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import uuid4

from fastapi import HTTPException, status

from apps.api.app.domain.scheduling.entities import (
    ApprovalDecision,
    ApprovalDecisionType,
    ApprovalTargetType,
    AssignmentType,
    AuditEvent,
    ChangeRequest,
    ChangeRequestStatus,
    ChangeRequestType,
    Department,
    ScheduleCalendar,
    SchedulePeriod,
    SchedulePeriodStatus,
    ShiftAssignment,
    Worker,
)
from apps.api.app.domain.scheduling.repository import InMemorySchedulingRepository


class SchedulingService:
    def __init__(self, repository: InMemorySchedulingRepository) -> None:
        self.repository = repository

    def create_department(self, *, name: str, code: str) -> Department:
        department = Department(id=self._new_id("dep"), name=name, code=code)
        created = self.repository.create_department(department)
        self._record_event(
            actor_id="system",
            entity_type="department",
            entity_id=created.id,
            action="department.created",
            payload={"name": created.name, "code": created.code},
        )
        return created

    def create_worker(
        self,
        *,
        full_name: str,
        document_id: str,
        worker_type: str,
        department_id: str,
    ) -> Worker:
        self._require_department(department_id)
        worker = Worker(
            id=self._new_id("wrk"),
            full_name=full_name,
            document_id=document_id,
            worker_type=worker_type,
            department_id=department_id,
        )
        created = self.repository.create_worker(worker)
        self._record_event(
            actor_id="system",
            entity_type="worker",
            entity_id=created.id,
            action="worker.created",
            payload={"department_id": created.department_id, "worker_type": created.worker_type},
        )
        return created

    def create_period(
        self,
        *,
        year: int,
        month: int,
        department_id: str,
        created_by: str | None,
    ) -> SchedulePeriod:
        self._require_department(department_id)
        if month < 1 or month > 12:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="month must be between 1 and 12")
        period = SchedulePeriod(
            id=self._new_id("sp"),
            year=year,
            month=month,
            department_id=department_id,
            created_by=created_by,
        )
        created = self.repository.create_period(period)
        self._record_event(
            actor_id=created_by or "system",
            entity_type="schedule_period",
            entity_id=created.id,
            action="schedule_period.created",
            payload={"year": created.year, "month": created.month, "department_id": created.department_id},
        )
        return created

    def get_period(self, period_id: str) -> SchedulePeriod:
        period = self.repository.get_period(period_id)
        if period is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="schedule period not found")
        return period

    def update_period_status(self, period_id: str, *, status_value: SchedulePeriodStatus) -> SchedulePeriod:
        period = self.get_period(period_id)
        period.status = status_value
        updated = self.repository.update_period(period)
        self._record_event(
            actor_id="system",
            entity_type="schedule_period",
            entity_id=updated.id,
            action="schedule_period.status_updated",
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
        if end_time <= start_time:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="end_time must be after start_time")
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
            actor_id="system",
            entity_type="assignment",
            entity_id=created.id,
            action="assignment.created",
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
        if end_time <= start_time:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="end_time must be after start_time")
        assignment.start_time = start_time
        assignment.end_time = end_time
        assignment.notes = notes
        updated = self.repository.update_assignment(assignment)
        self._record_event(
            actor_id="system",
            entity_type="assignment",
            entity_id=updated.id,
            action="assignment.updated",
            payload={"start_time": str(updated.start_time), "end_time": str(updated.end_time), "notes": updated.notes},
        )
        return updated

    def get_calendar(self, period_id: str) -> ScheduleCalendar:
        period = self.get_period(period_id)
        assignments = self.repository.list_assignments_for_period(period_id)
        assignments.sort(key=lambda item: (item.shift_date, item.start_time, item.worker_id))
        return ScheduleCalendar(period=period, assignments=assignments)

    def create_change_request(
        self,
        *,
        assignment_id: str,
        requested_by: str,
        request_type: ChangeRequestType,
        reason: str,
        replacement_worker_id: str | None,
    ) -> ChangeRequest:
        assignment = self.repository.get_assignment(assignment_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assignment not found")
        if not reason.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="reason is required")
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
            action="change_request.created",
            payload={"assignment_id": created.assignment_id, "request_type": created.request_type},
        )
        return created

    def get_change_request(self, request_id: str) -> ChangeRequest:
        change_request = self.repository.get_change_request(request_id)
        if change_request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="change request not found")
        return change_request

    def update_change_request_status(
        self,
        request_id: str,
        *,
        status_value: ChangeRequestStatus,
    ) -> ChangeRequest:
        change_request = self.get_change_request(request_id)
        if change_request.status != ChangeRequestStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="only pending change requests can be updated")
        if status_value not in {ChangeRequestStatus.CANCELLED, ChangeRequestStatus.APPROVED, ChangeRequestStatus.REJECTED}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid change request status transition")
        change_request.status = status_value
        updated = self.repository.update_change_request(change_request)
        self._record_event(
            actor_id=updated.requested_by,
            entity_type="change_request",
            entity_id=updated.id,
            action="change_request.status_updated",
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
            action="approval_decision.created",
            payload={"target_type": created.target_type, "target_id": created.target_id, "decision": created.decision},
        )
        return created

    def list_review_queue(self) -> dict[str, list[object]]:
        periods = [period for period in self.repository.periods.values() if period.status == SchedulePeriodStatus.IN_REVIEW]
        requests = [
            change_request
            for change_request in self.repository.change_requests.values()
            if change_request.status == ChangeRequestStatus.PENDING
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
        if period.status != SchedulePeriodStatus.IN_REVIEW:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="schedule period must be in_review before approval")
        period.status = (
            SchedulePeriodStatus.APPROVED
            if decision == ApprovalDecisionType.APPROVED
            else SchedulePeriodStatus.DRAFT
        )
        self.repository.update_period(period)

    def _apply_change_request_decision(self, request_id: str, decision: ApprovalDecisionType) -> None:
        change_request = self.get_change_request(request_id)
        if change_request.status != ChangeRequestStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="change request must be pending before approval")
        change_request.status = (
            ChangeRequestStatus.APPROVED
            if decision == ApprovalDecisionType.APPROVED
            else ChangeRequestStatus.REJECTED
        )
        self.repository.update_change_request(change_request)
        self._record_event(
            actor_id="system",
            entity_type="change_request",
            entity_id=change_request.id,
            action="change_request.reviewed",
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

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:8]}"
