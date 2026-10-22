from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime

from fastapi import HTTPException, status

from apps.api.app.domain.scheduling.entities import (
    ApprovalDecisionType,
    AttendanceDecisionStatus,
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
    ASSIGNMENT_REASSIGNED = "assignment.reassigned"
    CHANGE_REQUEST_CREATED = "change_request.created"
    CHANGE_REQUEST_STATUS_UPDATED = "change_request.status_updated"
    CHANGE_REQUEST_REVIEWED = "change_request.reviewed"
    APPROVAL_DECISION_CREATED = "approval_decision.created"
    EXPORT_CREATED = "export.created"
    ATTENDANCE_ENROLLMENT_CREATED = "attendance_enrollment.created"
    ATTENDANCE_ATTEMPT_CREATED = "attendance_attempt.created"
    ATTENDANCE_ATTEMPT_REVIEWED = "attendance_attempt.reviewed"


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


def validate_shift_date_in_period(*, shift_date, year: int, month: int) -> None:
    if (shift_date.year, shift_date.month) != (year, month):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"shift_date must fall inside {year}-{month:02d}",
        )


def validate_schedule_period_editable(status_value: SchedulePeriodStatus) -> None:
    if status_value != SchedulePeriodStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="schedule period must be draft to edit assignments",
        )


def validate_schedule_period_status_transition(
    *,
    current_status: SchedulePeriodStatus,
    next_status: SchedulePeriodStatus,
) -> None:
    allowed = {
        SchedulePeriodStatus.DRAFT: {SchedulePeriodStatus.IN_REVIEW},
        SchedulePeriodStatus.IN_REVIEW: {SchedulePeriodStatus.DRAFT, SchedulePeriodStatus.APPROVED},
        SchedulePeriodStatus.APPROVED: {SchedulePeriodStatus.CLOSED},
        SchedulePeriodStatus.CLOSED: set(),
    }
    if next_status == current_status:
        return
    if next_status not in allowed[current_status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="invalid schedule period status transition",
        )


def ensure_unique_department_code(existing_codes: set[str], code: str) -> None:
    if code.casefold() in existing_codes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="department code already exists",
        )


def ensure_unique_worker_document(existing_document_ids: set[str], document_id: str) -> None:
    if document_id.casefold() in existing_document_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="worker document_id already exists",
        )


def ensure_unique_schedule_period(existing_period_keys: set[tuple[str, int, int]], department_id: str, year: int, month: int) -> None:
    if (department_id, year, month) in existing_period_keys:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="schedule period already exists for department and month",
        )


def ensure_no_assignment_overlap(overlaps: bool) -> None:
    if overlaps:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="worker already has an overlapping assignment",
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


def _csv(rows: list[list[object]]) -> str:
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    return buffer.getvalue().rstrip("\n")


def _hours(assignment) -> float:
    start = datetime.combine(assignment.shift_date, assignment.start_time)
    end = datetime.combine(assignment.shift_date, assignment.end_time)
    return (end - start).total_seconds() / 3600


def build_export_table(*, export_type: ExportType, assignments, workers: dict, latest_attempts: dict) -> str:
    """CSV body of an export. ``workers`` maps id -> Worker, ``latest_attempts`` maps assignment id -> latest attempt."""
    ordered = sorted(assignments, key=lambda item: (item.shift_date, item.start_time, item.worker_id))

    def name(worker_id: str) -> str:
        worker = workers.get(worker_id)
        return worker.full_name if worker else worker_id

    if export_type == ExportType.PAYROLL_SUMMARY:
        totals: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
        for item in ordered:
            totals[item.worker_id][0] += 1
            totals[item.worker_id][1] += _hours(item)
        rows: list[list[object]] = [["worker", "worker_type", "shifts", "hours"]]
        for worker_id in sorted(totals, key=name):
            worker = workers.get(worker_id)
            rows.append([name(worker_id), worker.worker_type if worker else "", int(totals[worker_id][0]), f"{totals[worker_id][1]:.2f}"])
        return _csv(rows)

    if export_type == ExportType.COMPLIANCE_REPORT:
        rows = [["date", "start", "end", "worker", "attendance", "decided_by", "review_reason"]]
        for item in ordered:
            attempt = latest_attempts.get(item.id)
            rows.append(
                [
                    item.shift_date.isoformat(),
                    item.start_time.strftime("%H:%M"),
                    item.end_time.strftime("%H:%M"),
                    name(item.worker_id),
                    attempt.decision_status.value if attempt else "no_record",
                    (attempt.decided_by or "") if attempt else "",
                    (attempt.review_reason or "") if attempt else "",
                ]
            )
        return _csv(rows)

    rows = [["date", "start", "end", "worker", "role", "assignment_type", "notes"]]
    for item in ordered:
        worker = workers.get(item.worker_id)
        rows.append(
            [
                item.shift_date.isoformat(),
                item.start_time.strftime("%H:%M"),
                item.end_time.strftime("%H:%M"),
                name(item.worker_id),
                worker.worker_type if worker else "",
                item.assignment_type.value,
                item.notes or "",
            ]
        )
    return _csv(rows)


def require_active_attendance_enrollment(is_active: bool) -> None:
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="worker must have an active attendance enrollment",
        )


def require_pending_attendance_attempt(status_value: AttendanceDecisionStatus) -> None:
    if status_value != AttendanceDecisionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="only pending attendance attempts can be reviewed",
        )
