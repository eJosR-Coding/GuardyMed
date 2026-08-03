from __future__ import annotations

from collections import defaultdict

from apps.api.app.domain.scheduling.entities import (
    ApprovalDecision,
    AuditEvent,
    ChangeRequest,
    Department,
    ExportJob,
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
        self.exports: dict[str, ExportJob] = {}
        self.exports_by_period: dict[str, list[str]] = defaultdict(list)

    def create_department(self, department: Department) -> Department:
        self.departments[department.id] = department
        return department

    def get_department(self, department_id: str) -> Department | None:
        return self.departments.get(department_id)

    def list_departments(self) -> list[Department]:
        return sorted(self.departments.values(), key=lambda item: item.name.lower())

    def create_worker(self, worker: Worker) -> Worker:
        self.workers[worker.id] = worker
        return worker

    def get_worker(self, worker_id: str) -> Worker | None:
        return self.workers.get(worker_id)

    def list_workers(self, department_id: str | None = None) -> list[Worker]:
        workers = list(self.workers.values())
        if department_id is not None:
            workers = [item for item in workers if item.department_id == department_id]
        return sorted(workers, key=lambda item: item.full_name.lower())

    def create_period(self, period: SchedulePeriod) -> SchedulePeriod:
        self.periods[period.id] = period
        return period

    def get_period(self, period_id: str) -> SchedulePeriod | None:
        return self.periods.get(period_id)

    def list_periods(self, department_id: str | None = None) -> list[SchedulePeriod]:
        periods = list(self.periods.values())
        if department_id is not None:
            periods = [item for item in periods if item.department_id == department_id]
        return sorted(periods, key=lambda item: (item.year, item.month, item.id), reverse=True)

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

    def list_assignments_for_worker(self, worker_id: str) -> list[ShiftAssignment]:
        assignments = [item for item in self.assignments.values() if item.worker_id == worker_id]
        return sorted(assignments, key=lambda item: (item.shift_date, item.start_time, item.id))

    def create_change_request(self, change_request: ChangeRequest) -> ChangeRequest:
        self.change_requests[change_request.id] = change_request
        self.requests_by_assignment[change_request.assignment_id].append(change_request.id)
        return change_request

    def get_change_request(self, request_id: str) -> ChangeRequest | None:
        return self.change_requests.get(request_id)

    def list_change_requests(self, requested_by: str | None = None) -> list[ChangeRequest]:
        requests = list(self.change_requests.values())
        if requested_by is not None:
            requests = [item for item in requests if item.requested_by == requested_by]
        return sorted(requests, key=lambda item: item.id, reverse=True)

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

    def create_export(self, export_job: ExportJob) -> ExportJob:
        self.exports[export_job.id] = export_job
        self.exports_by_period[export_job.schedule_period_id].append(export_job.id)
        return export_job

    def get_export(self, export_id: str) -> ExportJob | None:
        return self.exports.get(export_id)

    def list_exports_for_period(self, period_id: str) -> list[ExportJob]:
        ids = self.exports_by_period[period_id]
        return [self.exports[item_id] for item_id in ids]
