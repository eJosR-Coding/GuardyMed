from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.api.app.domain.scheduling.entities import AssignmentType, SchedulePeriodStatus
from apps.api.app.domain.scheduling.entities import (
    ApprovalDecisionType,
    ApprovalTargetType,
    ChangeRequestStatus,
    ChangeRequestType,
    ExportType,
)


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    code: str = Field(min_length=2, max_length=20)

    @field_validator("name", "code")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value is required")
        return cleaned


class DepartmentRead(DepartmentCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)


class WorkerCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    document_id: str = Field(min_length=6, max_length=20)
    worker_type: str = Field(min_length=2, max_length=60)
    department_id: str

    @field_validator("full_name", "document_id", "worker_type")
    @classmethod
    def strip_worker_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value is required")
        return cleaned


class WorkerRead(WorkerCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)


class SchedulePeriodCreate(BaseModel):
    year: int
    month: int
    department_id: str
    created_by: str | None = None

    @field_validator("created_by")
    @classmethod
    def strip_created_by(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


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


class SchedulePeriodListRead(BaseModel):
    items: list[SchedulePeriodRead]


class ShiftAssignmentCreate(BaseModel):
    worker_id: str
    assignment_type: AssignmentType
    shift_date: date
    start_time: time
    end_time: time
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ShiftAssignmentUpdate(BaseModel):
    start_time: time
    end_time: time
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("notes")
    @classmethod
    def strip_update_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


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


class ShiftAssignmentListRead(BaseModel):
    items: list[ShiftAssignmentRead]


class ChangeRequestCreate(BaseModel):
    requested_by: str | None = None
    request_type: ChangeRequestType
    reason: str = Field(min_length=4, max_length=400)
    replacement_worker_id: str | None = None

    @field_validator("requested_by", "replacement_worker_id")
    @classmethod
    def strip_optional_ids(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("reason is required")
        return cleaned


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


class ChangeRequestListRead(BaseModel):
    items: list[ChangeRequestRead]


class ApprovalDecisionCreate(BaseModel):
    target_type: ApprovalTargetType
    target_id: str
    decision: ApprovalDecisionType
    decided_by: str | None = None
    comment: str | None = Field(default=None, max_length=300)

    @field_validator("target_id", "decided_by", "comment")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ApprovalDecisionRead(BaseModel):
    id: str
    target_type: ApprovalTargetType
    target_id: str
    decision: ApprovalDecisionType
    decided_by: str
    comment: str | None

    model_config = ConfigDict(from_attributes=True)


class ReviewQueueRead(BaseModel):
    schedule_periods: list[SchedulePeriodRead]
    change_requests: list[ChangeRequestRead]


class AuditEventRead(BaseModel):
    id: str
    actor_id: str
    entity_type: str
    entity_id: str
    action: str
    payload: dict[str, object]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExportCreate(BaseModel):
    export_type: ExportType
    created_by: str | None = None

    @field_validator("created_by")
    @classmethod
    def strip_export_created_by(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ExportRead(BaseModel):
    id: str
    schedule_period_id: str
    export_type: ExportType
    created_by: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduleCalendarRead(BaseModel):
    period: SchedulePeriodRead
    assignments: list[ShiftAssignmentRead]


class DemoSeedRead(BaseModel):
    seeded: bool
    departments: int
    workers: int
    periods: int
    assignments: int
    change_requests: int
