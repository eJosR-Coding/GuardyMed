from __future__ import annotations

from collections import defaultdict

from apps.api.app.domain.scheduling.entities import (
    ApprovalDecision,
    AuditEvent,
    ChangeRequest,
    Department,
    SchedulePeriod,
    ShiftAssignment,
    Worker,
)


class InMemorySchedulingRepository:
    def __init__(self) -> None:
        self.departments: dict[str, Department] = {}
        self.workers: dict[str, Worker] = {}
        self.periods: dict[str, SchedulePeriod] = {}
        self.assignments: dict[str, ShiftAssignment] = {}
        self.assignments_by_period: dict[str, list[str]] = defaultdict(list)
        self.change_requests: dict[str, ChangeRequest] = {}
        self.requests_by_assignment: dict[str, list[str]] = defaultdict(list)
        self.approval_decisions: dict[str, ApprovalDecision] = {}
        self.audit_events: dict[str, AuditEvent] = {}
        self.audit_events_by_entity: dict[tuple[str, str], list[str]] = defaultdict(list)

    def create_department(self, department: Department) -> Department:
        self.departments[department.id] = department
        return department

    def get_department(self, department_id: str) -> Department | None:
        return self.departments.get(department_id)

    def create_worker(self, worker: Worker) -> Worker:
        self.workers[worker.id] = worker
        return worker

    def get_worker(self, worker_id: str) -> Worker | None:
        return self.workers.get(worker_id)

    def create_period(self, period: SchedulePeriod) -> SchedulePeriod:
        self.periods[period.id] = period
        return period

    def get_period(self, period_id: str) -> SchedulePeriod | None:
        return self.periods.get(period_id)

    def update_period(self, period: SchedulePeriod) -> SchedulePeriod:
        self.periods[period.id] = period
        return period

    def create_assignment(self, assignment: ShiftAssignment) -> ShiftAssignment:
        self.assignments[assignment.id] = assignment
        self.assignments_by_period[assignment.schedule_period_id].append(assignment.id)
        return assignment

    def get_assignment(self, assignment_id: str) -> ShiftAssignment | None:
        return self.assignments.get(assignment_id)

    def update_assignment(self, assignment: ShiftAssignment) -> ShiftAssignment:
        self.assignments[assignment.id] = assignment
        return assignment

    def list_assignments_for_period(self, period_id: str) -> list[ShiftAssignment]:
        return [self.assignments[item_id] for item_id in self.assignments_by_period[period_id]]

    def create_change_request(self, change_request: ChangeRequest) -> ChangeRequest:
        self.change_requests[change_request.id] = change_request
        self.requests_by_assignment[change_request.assignment_id].append(change_request.id)
        return change_request

    def get_change_request(self, request_id: str) -> ChangeRequest | None:
        return self.change_requests.get(request_id)

    def update_change_request(self, change_request: ChangeRequest) -> ChangeRequest:
        self.change_requests[change_request.id] = change_request
        return change_request

    def create_approval_decision(self, approval_decision: ApprovalDecision) -> ApprovalDecision:
        self.approval_decisions[approval_decision.id] = approval_decision
        return approval_decision

    def create_audit_event(self, audit_event: AuditEvent) -> AuditEvent:
        self.audit_events[audit_event.id] = audit_event
        self.audit_events_by_entity[(audit_event.entity_type, audit_event.entity_id)].append(audit_event.id)
        return audit_event

    def list_audit_events(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> list[AuditEvent]:
        if entity_type and entity_id:
            ids = self.audit_events_by_entity[(entity_type, entity_id)]
            return [self.audit_events[item_id] for item_id in ids]
        events = list(self.audit_events.values())
        events.sort(key=lambda item: item.created_at)
        return events
