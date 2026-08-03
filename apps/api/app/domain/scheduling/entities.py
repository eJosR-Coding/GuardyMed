from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
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


class ApprovalTargetType(StrEnum):
    SCHEDULE_PERIOD = "schedule_period"
    CHANGE_REQUEST = "change_request"


class ApprovalDecisionType(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ExportType(StrEnum):
    OPERATIONAL_SUMMARY = "operational_summary"
    PAYROLL_SUMMARY = "payroll_summary"
    COMPLIANCE_REPORT = "compliance_report"


class AttendanceEnrollmentStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class AttendanceAttemptType(StrEnum):
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"


class AttendanceDecisionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


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
class ApprovalDecision:
    id: str
    target_type: ApprovalTargetType
    target_id: str
    decision: ApprovalDecisionType
    decided_by: str
    comment: str | None = None


@dataclass(slots=True)
class AuditEvent:
    id: str
    actor_id: str
    entity_type: str
    entity_id: str
    action: str
    payload: dict[str, object]
    created_at: datetime


@dataclass(slots=True)
class ExportJob:
    id: str
    schedule_period_id: str
    export_type: ExportType
    created_by: str
    content: str
    created_at: datetime


@dataclass(slots=True)
class ScheduleCalendar:
    period: SchedulePeriod
    assignments: list[ShiftAssignment] = field(default_factory=list)


@dataclass(slots=True)
class AttendanceEnrollment:
    id: str
    worker_id: str
    status: AttendanceEnrollmentStatus
    created_by: str
    created_at: datetime


@dataclass(slots=True)
class AttendanceAttempt:
    id: str
    worker_id: str
    assignment_id: str
    attempt_type: AttendanceAttemptType
    evidence_ref: str | None
    attempted_at: datetime
    decision_status: AttendanceDecisionStatus = AttendanceDecisionStatus.PENDING
    review_reason: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
