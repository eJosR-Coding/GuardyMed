from __future__ import annotations

from fastapi import HTTPException, status

from apps.api.app.domain.scheduling.entities import (
    ApprovalDecisionType,
    ChangeRequestStatus,
    ExportType,
    SchedulePeriodStatus,
)


SYSTEM_ACTOR_ID = "system"


class AuditAction:
    DEPARTMENT_CREATED = "department.created"
    WORKER_CREATED = "worker.created"
    SCHEDULE_PERIOD_CREATED = "schedule_period.created"
    SCHEDULE_PERIOD_STATUS_UPDATED = "schedule_period.status_updated"
    ASSIGNMENT_CREATED = "assignment.created"
    ASSIGNMENT_UPDATED = "assignment.updated"
    CHANGE_REQUEST_CREATED = "change_request.created"
    CHANGE_REQUEST_STATUS_UPDATED = "change_request.status_updated"
    CHANGE_REQUEST_REVIEWED = "change_request.reviewed"
    APPROVAL_DECISION_CREATED = "approval_decision.created"
    EXPORT_CREATED = "export.created"


def validate_month(month: int) -> None:
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="month must be between 1 and 12",
        )


def validate_time_window(*, start_time, end_time) -> None:
    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="end_time must be after start_time",
        )


def require_pending_change_request(status_value: ChangeRequestStatus) -> None:
    if status_value != ChangeRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="only pending change requests can be updated",
        )


def validate_change_request_status_transition(
    next_status: ChangeRequestStatus,
) -> None:
    if next_status not in {
        ChangeRequestStatus.CANCELLED,
        ChangeRequestStatus.APPROVED,
        ChangeRequestStatus.REJECTED,
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid change request status transition",
        )


def next_schedule_period_status_from_decision(
    *,
    current_status: SchedulePeriodStatus,
    decision: ApprovalDecisionType,
) -> SchedulePeriodStatus:
    if current_status != SchedulePeriodStatus.IN_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="schedule period must be in_review before approval",
        )
    return (
        SchedulePeriodStatus.APPROVED
        if decision == ApprovalDecisionType.APPROVED
        else SchedulePeriodStatus.DRAFT
    )


def next_change_request_status_from_decision(
    *,
    current_status: ChangeRequestStatus,
    decision: ApprovalDecisionType,
) -> ChangeRequestStatus:
    if current_status != ChangeRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="change request must be pending before approval",
        )
    return (
        ChangeRequestStatus.APPROVED
        if decision == ApprovalDecisionType.APPROVED
        else ChangeRequestStatus.REJECTED
    )


def validate_exportable_period(status_value: SchedulePeriodStatus) -> None:
    if status_value not in {SchedulePeriodStatus.APPROVED, SchedulePeriodStatus.CLOSED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="schedule period must be approved before export",
        )


def build_export_lines(
    *,
    export_type: ExportType,
    year: int,
    month: int,
    department_id: str,
    assignment_count: int,
    worker_count: int,
) -> list[str]:
    return [
        f"export_type={export_type}",
        f"period={year}-{month:02d}",
        f"department_id={department_id}",
        f"assignments={assignment_count}",
        f"workers={worker_count}",
    ]
