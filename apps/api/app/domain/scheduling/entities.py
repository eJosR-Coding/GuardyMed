from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from enum import StrEnum


class SchedulePeriodStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    CLOSED = "closed"


class AssignmentType(StrEnum):
    GUARD_SHIFT = "guard_shift"
    SHIFT_LEAD = "shift_lead"
    ON_CALL = "on_call"


@dataclass(slots=True)
class Department:
    id: str
    name: str
    code: str


@dataclass(slots=True)
class Worker:
    id: str
    full_name: str
    document_id: str
    worker_type: str
    department_id: str


@dataclass(slots=True)
class SchedulePeriod:
    id: str
    year: int
    month: int
    department_id: str
    created_by: str | None = None
    status: SchedulePeriodStatus = SchedulePeriodStatus.DRAFT


@dataclass(slots=True)
class ShiftAssignment:
    id: str
    schedule_period_id: str
    worker_id: str
    assignment_type: AssignmentType
    shift_date: date
    start_time: time
    end_time: time
    notes: str | None = None


@dataclass(slots=True)
class ScheduleCalendar:
    period: SchedulePeriod
    assignments: list[ShiftAssignment] = field(default_factory=list)
