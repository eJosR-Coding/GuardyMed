from __future__ import annotations

from datetime import date, time
from uuid import uuid4

from fastapi import HTTPException, status

from apps.api.app.domain.scheduling.entities import (
    AssignmentType,
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
        return self.repository.create_department(department)

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
        return self.repository.create_worker(worker)

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
        return self.repository.create_period(period)

    def get_period(self, period_id: str) -> SchedulePeriod:
        period = self.repository.get_period(period_id)
        if period is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="schedule period not found")
        return period

    def update_period_status(self, period_id: str, *, status_value: SchedulePeriodStatus) -> SchedulePeriod:
        period = self.get_period(period_id)
        period.status = status_value
        return self.repository.update_period(period)

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
        return self.repository.create_assignment(assignment)

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
        return self.repository.update_assignment(assignment)

    def get_calendar(self, period_id: str) -> ScheduleCalendar:
        period = self.get_period(period_id)
        assignments = self.repository.list_assignments_for_period(period_id)
        assignments.sort(key=lambda item: (item.shift_date, item.start_time, item.worker_id))
        return ScheduleCalendar(period=period, assignments=assignments)

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

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:8]}"
