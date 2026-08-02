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


class ChangeRequestType(StrEnum):
    SWAP = "swap"
    REPLACEMENT = "replacement"
    INCIDENT = "incident"
    ADJUSTMENT = "adjustment"


class ChangeRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


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
class ChangeRequest:
    id: str
    assignment_id: str
    requested_by: str
    request_type: ChangeRequestType
    reason: str
    status: ChangeRequestStatus = ChangeRequestStatus.PENDING
    replacement_worker_id: str | None = None


@dataclass(slots=True)
class ScheduleCalendar:
    period: SchedulePeriod
    assignments: list[ShiftAssignment] = field(default_factory=list)
