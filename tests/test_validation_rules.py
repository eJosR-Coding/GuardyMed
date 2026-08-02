from datetime import time

from fastapi import HTTPException

from apps.api.app.domain.scheduling.entities import (
    ApprovalDecisionType,
    ChangeRequestStatus,
    ExportType,
    SchedulePeriodStatus,
)
from apps.api.app.domain.scheduling.rules import (
    AuditAction,
    build_export_lines,
    next_change_request_status_from_decision,
    next_schedule_period_status_from_decision,
    validate_change_request_status_transition,
    validate_exportable_period,
    validate_month,
    validate_time_window,
)


def test_audit_action_constants_are_stable() -> None:
    assert AuditAction.SCHEDULE_PERIOD_CREATED == "schedule_period.created"
    assert AuditAction.EXPORT_CREATED == "export.created"


def test_validate_month_rejects_invalid_value() -> None:
    try:
        validate_month(13)
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "month must be between 1 and 12"
    else:
        raise AssertionError("expected invalid month to fail")


def test_validate_time_window_rejects_invalid_range() -> None:
    try:
        validate_time_window(start_time=time(20, 0), end_time=time(8, 0))
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "end_time must be after start_time"
    else:
        raise AssertionError("expected invalid time window to fail")


def test_change_request_transition_rules_are_centralized() -> None:
    validate_change_request_status_transition(ChangeRequestStatus.CANCELLED)
    try:
        validate_change_request_status_transition(ChangeRequestStatus.PENDING)
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "invalid change request status transition"
    else:
        raise AssertionError("expected invalid transition to fail")


def test_schedule_period_decision_transition_is_explicit() -> None:
    approved = next_schedule_period_status_from_decision(
        current_status=SchedulePeriodStatus.IN_REVIEW,
        decision=ApprovalDecisionType.APPROVED,
    )
    rejected = next_schedule_period_status_from_decision(
        current_status=SchedulePeriodStatus.IN_REVIEW,
        decision=ApprovalDecisionType.REJECTED,
    )

    assert approved == SchedulePeriodStatus.APPROVED
    assert rejected == SchedulePeriodStatus.DRAFT


def test_change_request_decision_transition_is_explicit() -> None:
    approved = next_change_request_status_from_decision(
        current_status=ChangeRequestStatus.PENDING,
        decision=ApprovalDecisionType.APPROVED,
    )
    rejected = next_change_request_status_from_decision(
        current_status=ChangeRequestStatus.PENDING,
        decision=ApprovalDecisionType.REJECTED,
    )

    assert approved == ChangeRequestStatus.APPROVED
    assert rejected == ChangeRequestStatus.REJECTED


def test_export_rules_are_centralized() -> None:
    validate_exportable_period(SchedulePeriodStatus.APPROVED)
    lines = build_export_lines(
        export_type=ExportType.OPERATIONAL_SUMMARY,
        year=2026,
        month=8,
        department_id="dep_1",
        assignment_count=3,
        worker_count=2,
    )

    assert "assignments=3" in lines
    assert "workers=2" in lines
