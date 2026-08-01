from __future__ import annotations

from collections import defaultdict

from apps.api.app.domain.scheduling.entities import (
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
