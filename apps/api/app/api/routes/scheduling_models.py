from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, ConfigDict

from apps.api.app.domain.scheduling.entities import AssignmentType, SchedulePeriodStatus


class DepartmentCreate(BaseModel):
    name: str
    code: str


class DepartmentRead(DepartmentCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)


class WorkerCreate(BaseModel):
    full_name: str
    document_id: str
    worker_type: str
    department_id: str


class WorkerRead(WorkerCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)


class SchedulePeriodCreate(BaseModel):
    year: int
    month: int
    department_id: str
    created_by: str | None = None


class SchedulePeriodUpdate(BaseModel):
    status: SchedulePeriodStatus


class SchedulePeriodRead(BaseModel):
    id: str
    year: int
    month: int
    department_id: str
    created_by: str | None
    status: SchedulePeriodStatus

    model_config = ConfigDict(from_attributes=True)


class ShiftAssignmentCreate(BaseModel):
    worker_id: str
    assignment_type: AssignmentType
    shift_date: date
    start_time: time
    end_time: time
    notes: str | None = None


class ShiftAssignmentUpdate(BaseModel):
    start_time: time
    end_time: time
    notes: str | None = None


class ShiftAssignmentRead(BaseModel):
    id: str
    schedule_period_id: str
    worker_id: str
    assignment_type: AssignmentType
    shift_date: date
    start_time: time
    end_time: time
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class ScheduleCalendarRead(BaseModel):
    period: SchedulePeriodRead
    assignments: list[ShiftAssignmentRead]
