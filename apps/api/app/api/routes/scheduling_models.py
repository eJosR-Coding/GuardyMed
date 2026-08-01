from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, ConfigDict

from apps.api.app.domain.scheduling.entities import AssignmentType, SchedulePeriodStatus
from apps.api.app.domain.scheduling.entities import ChangeRequestStatus, ChangeRequestType


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


class ChangeRequestCreate(BaseModel):
    requested_by: str
    request_type: ChangeRequestType
    reason: str
    replacement_worker_id: str | None = None


class ChangeRequestUpdate(BaseModel):
    status: ChangeRequestStatus


class ChangeRequestRead(BaseModel):
    id: str
    assignment_id: str
    requested_by: str
    request_type: ChangeRequestType
    reason: str
    status: ChangeRequestStatus
    replacement_worker_id: str | None

    model_config = ConfigDict(from_attributes=True)


class ScheduleCalendarRead(BaseModel):
    period: SchedulePeriodRead
    assignments: list[ShiftAssignmentRead]
