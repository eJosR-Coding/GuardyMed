from datetime import date, time

from apps.api.app.domain.scheduling.entities import (
    ApprovalDecisionType,
    ApprovalTargetType,
    AssignmentType,
    ChangeRequestStatus,
    ChangeRequestType,
    ExportType,
    SchedulePeriodStatus,
)
from apps.api.app.domain.scheduling.repository import InMemorySchedulingRepository
from apps.api.app.domain.scheduling.service import SchedulingService


def build_service() -> SchedulingService:
    return SchedulingService(InMemorySchedulingRepository())


def test_create_schedule_period_flow() -> None:
    service = build_service()

    department = service.create_department(name="Emergency", code="ER")
    worker = service.create_worker(
        full_name="Ada Lovelace",
        document_id="12345678",
        worker_type="nurse",
        department_id=department.id,
    )
    period = service.create_period(
        year=2026,
        month=8,
        department_id=department.id,
        created_by="coordinator_1",
    )

    assignment = service.create_assignment(
        period_id=period.id,
        worker_id=worker.id,
        assignment_type=AssignmentType.GUARD_SHIFT,
        shift_date=date(2026, 8, 3),
        start_time=time(8, 0),
        end_time=time(20, 0),
        notes="day shift",
    )

    updated_assignment = service.update_assignment(
        assignment.id,
        start_time=time(9, 0),
        end_time=time(21, 0),
        notes="updated shift",
    )
    updated_period = service.update_period_status(period.id, status_value=SchedulePeriodStatus.IN_REVIEW)
    calendar = service.get_calendar(period.id)

    assert updated_period.status == SchedulePeriodStatus.IN_REVIEW
    assert updated_assignment.notes == "updated shift"
    assert calendar.period.id == period.id
    assert len(calendar.assignments) == 1
    assert calendar.assignments[0].worker_id == worker.id


def test_assignment_rejects_invalid_time_window() -> None:
    service = build_service()

    department = service.create_department(name="ICU", code="ICU")
    worker = service.create_worker(
        full_name="Grace Hopper",
        document_id="87654321",
        worker_type="doctor",
        department_id=department.id,
    )
    period = service.create_period(
        year=2026,
        month=9,
        department_id=department.id,
        created_by=None,
    )

    try:
        service.create_assignment(
            period_id=period.id,
            worker_id=worker.id,
            assignment_type=AssignmentType.GUARD_SHIFT,
            shift_date=date(2026, 9, 1),
            start_time=time(20, 0),
            end_time=time(8, 0),
            notes=None,
        )
    except Exception as exc:  # ponytail: FastAPI HTTPException is enough until domain errors exist
        assert getattr(exc, "status_code", None) == 422
        assert getattr(exc, "detail", None) == "end_time must be after start_time"
    else:
        raise AssertionError("expected assignment creation to fail")


def test_app_routes_are_registered() -> None:
    from apps.api.app.main import app

    paths = {route.path for route in app.routes}

    assert "/health" in paths
    assert "/api/v1/scheduling/schedule-periods" in paths
    assert "/api/v1/scheduling/schedule-periods/{period_id}/assignments" in paths
    assert "/api/v1/scheduling/assignments/{assignment_id}/change-requests" in paths
    assert "/api/v1/scheduling/review-queue" in paths
    assert "/api/v1/scheduling/approval-decisions" in paths
    assert "/api/v1/scheduling/audit-events" in paths
    assert "/api/v1/scheduling/schedule-periods/{period_id}/exports" in paths
    assert "/api/v1/scheduling/exports/{export_id}" in paths


def test_create_and_cancel_change_request() -> None:
    service = build_service()

    department = service.create_department(name="Emergency", code="ER")
    worker = service.create_worker(
        full_name="Ada Lovelace",
        document_id="12345678",
        worker_type="nurse",
        department_id=department.id,
    )
    period = service.create_period(
        year=2026,
        month=8,
        department_id=department.id,
        created_by="coordinator_1",
    )
    assignment = service.create_assignment(
        period_id=period.id,
        worker_id=worker.id,
        assignment_type=AssignmentType.GUARD_SHIFT,
        shift_date=date(2026, 8, 3),
        start_time=time(8, 0),
        end_time=time(20, 0),
        notes="day shift",
    )

    change_request = service.create_change_request(
        assignment_id=assignment.id,
        requested_by=worker.id,
        request_type=ChangeRequestType.ADJUSTMENT,
        reason="Need to adjust due to appointment",
        replacement_worker_id=None,
    )
    updated_request = service.update_change_request_status(
        change_request.id,
        status_value=ChangeRequestStatus.CANCELLED,
    )

    assert change_request.status == ChangeRequestStatus.CANCELLED
    assert updated_request.status == ChangeRequestStatus.CANCELLED
    assert updated_request.reason == "Need to adjust due to appointment"


def test_change_request_rejects_invalid_transition() -> None:
    service = build_service()

    department = service.create_department(name="Emergency", code="ER")
    worker = service.create_worker(
        full_name="Ada Lovelace",
        document_id="12345678",
        worker_type="nurse",
        department_id=department.id,
    )
    period = service.create_period(
        year=2026,
        month=8,
        department_id=department.id,
        created_by="coordinator_1",
    )
    assignment = service.create_assignment(
        period_id=period.id,
        worker_id=worker.id,
        assignment_type=AssignmentType.GUARD_SHIFT,
        shift_date=date(2026, 8, 3),
        start_time=time(8, 0),
        end_time=time(20, 0),
        notes="day shift",
    )
    change_request = service.create_change_request(
        assignment_id=assignment.id,
        requested_by=worker.id,
        request_type=ChangeRequestType.SWAP,
        reason="Need a swap",
        replacement_worker_id=None,
    )
    service.update_change_request_status(
        change_request.id,
        status_value=ChangeRequestStatus.CANCELLED,
    )

    try:
        service.update_change_request_status(
            change_request.id,
            status_value=ChangeRequestStatus.REJECTED,
        )
    except Exception as exc:  # ponytail: FastAPI HTTPException is enough until domain errors exist
        assert getattr(exc, "status_code", None) == 409
        assert getattr(exc, "detail", None) == "only pending change requests can be updated"
    else:
        raise AssertionError("expected change request update to fail")


def test_approve_schedule_period_from_review_queue() -> None:
    service = build_service()

    department = service.create_department(name="Emergency", code="ER")
    period = service.create_period(
        year=2026,
        month=8,
        department_id=department.id,
        created_by="coordinator_1",
    )
    service.update_period_status(period.id, status_value=SchedulePeriodStatus.IN_REVIEW)

    queue_before = service.list_review_queue()
    assert len(queue_before["schedule_periods"]) == 1

    decision = service.create_approval_decision(
        target_type=ApprovalTargetType.SCHEDULE_PERIOD,
        target_id=period.id,
        decision=ApprovalDecisionType.APPROVED,
        decided_by="approver_1",
        comment="approved",
    )

    updated_period = service.get_period(period.id)
    queue_after = service.list_review_queue()

    assert decision.target_id == period.id
    assert updated_period.status == SchedulePeriodStatus.APPROVED
    assert len(queue_after["schedule_periods"]) == 0


def test_reject_change_request_via_approval_decision() -> None:
    service = build_service()

    department = service.create_department(name="Emergency", code="ER")
    worker = service.create_worker(
        full_name="Ada Lovelace",
        document_id="12345678",
        worker_type="nurse",
        department_id=department.id,
    )
    period = service.create_period(
        year=2026,
        month=8,
        department_id=department.id,
        created_by="coordinator_1",
    )
    assignment = service.create_assignment(
        period_id=period.id,
        worker_id=worker.id,
        assignment_type=AssignmentType.GUARD_SHIFT,
        shift_date=date(2026, 8, 3),
        start_time=time(8, 0),
        end_time=time(20, 0),
        notes="day shift",
    )
    change_request = service.create_change_request(
        assignment_id=assignment.id,
        requested_by=worker.id,
        request_type=ChangeRequestType.SWAP,
        reason="Need a swap",
        replacement_worker_id=None,
    )

    decision = service.create_approval_decision(
        target_type=ApprovalTargetType.CHANGE_REQUEST,
        target_id=change_request.id,
        decision=ApprovalDecisionType.REJECTED,
        decided_by="approver_1",
        comment="not possible",
    )
    updated_request = service.get_change_request(change_request.id)

    assert decision.target_id == change_request.id
    assert updated_request.status == ChangeRequestStatus.REJECTED


def test_reject_schedule_period_returns_to_draft() -> None:
    service = build_service()

    department = service.create_department(name="Emergency", code="ER")
    period = service.create_period(
        year=2026,
        month=8,
        department_id=department.id,
        created_by="coordinator_1",
    )
    service.update_period_status(period.id, status_value=SchedulePeriodStatus.IN_REVIEW)

    service.create_approval_decision(
        target_type=ApprovalTargetType.SCHEDULE_PERIOD,
        target_id=period.id,
        decision=ApprovalDecisionType.REJECTED,
        decided_by="approver_1",
        comment="needs changes",
    )

    updated_period = service.get_period(period.id)
    assert updated_period.status == SchedulePeriodStatus.DRAFT


def test_audit_events_are_recorded_for_core_flow() -> None:
    service = build_service()

    department = service.create_department(name="Emergency", code="ER")
    worker = service.create_worker(
        full_name="Ada Lovelace",
        document_id="12345678",
        worker_type="nurse",
        department_id=department.id,
    )
    period = service.create_period(
        year=2026,
        month=8,
        department_id=department.id,
        created_by="coordinator_1",
    )
    assignment = service.create_assignment(
        period_id=period.id,
        worker_id=worker.id,
        assignment_type=AssignmentType.GUARD_SHIFT,
        shift_date=date(2026, 8, 3),
        start_time=time(8, 0),
        end_time=time(20, 0),
        notes="day shift",
    )
    change_request = service.create_change_request(
        assignment_id=assignment.id,
        requested_by=worker.id,
        request_type=ChangeRequestType.SWAP,
        reason="Need a swap",
        replacement_worker_id=None,
    )

    events = service.list_audit_events()
    assignment_events = service.list_audit_events(entity_type="assignment", entity_id=assignment.id)
    request_events = service.list_audit_events(entity_type="change_request", entity_id=change_request.id)

    assert len(events) >= 5
    assert any(event.action == "assignment.created" for event in assignment_events)
    assert any(event.action == "change_request.created" for event in request_events)


def test_audit_events_capture_approval_side_effects() -> None:
    service = build_service()

    department = service.create_department(name="Emergency", code="ER")
    period = service.create_period(
        year=2026,
        month=8,
        department_id=department.id,
        created_by="coordinator_1",
    )
    service.update_period_status(period.id, status_value=SchedulePeriodStatus.IN_REVIEW)
    decision = service.create_approval_decision(
        target_type=ApprovalTargetType.SCHEDULE_PERIOD,
        target_id=period.id,
        decision=ApprovalDecisionType.APPROVED,
        decided_by="approver_1",
        comment="approved",
    )

    period_events = service.list_audit_events(entity_type="schedule_period", entity_id=period.id)
    decision_events = service.list_audit_events(entity_type="approval_decision", entity_id=decision.id)

    assert any(event.action == "schedule_period.status_updated" for event in period_events)
    assert any(event.action == "approval_decision.created" for event in decision_events)


def test_create_and_fetch_export_for_approved_period() -> None:
    service = build_service()

    department = service.create_department(name="Emergency", code="ER")
    worker = service.create_worker(
        full_name="Ada Lovelace",
        document_id="12345678",
        worker_type="nurse",
        department_id=department.id,
    )
    period = service.create_period(
        year=2026,
        month=8,
        department_id=department.id,
        created_by="coordinator_1",
    )
    service.create_assignment(
        period_id=period.id,
        worker_id=worker.id,
        assignment_type=AssignmentType.GUARD_SHIFT,
        shift_date=date(2026, 8, 3),
        start_time=time(8, 0),
        end_time=time(20, 0),
        notes="day shift",
    )
    service.update_period_status(period.id, status_value=SchedulePeriodStatus.IN_REVIEW)
    service.create_approval_decision(
        target_type=ApprovalTargetType.SCHEDULE_PERIOD,
        target_id=period.id,
        decision=ApprovalDecisionType.APPROVED,
        decided_by="approver_1",
        comment="approved",
    )

    export_job = service.create_export(
        period_id=period.id,
        export_type=ExportType.OPERATIONAL_SUMMARY,
        created_by="admin_1",
    )
    fetched_export = service.get_export(export_job.id)
    period_exports = service.list_exports_for_period(period.id)

    assert fetched_export.id == export_job.id
    assert export_job.export_type == ExportType.OPERATIONAL_SUMMARY
    assert "assignments=1" in export_job.content
    assert len(period_exports) == 1


def test_export_requires_approved_period() -> None:
    service = build_service()

    department = service.create_department(name="Emergency", code="ER")
    period = service.create_period(
        year=2026,
        month=8,
        department_id=department.id,
        created_by="coordinator_1",
    )

    try:
        service.create_export(
            period_id=period.id,
            export_type=ExportType.COMPLIANCE_REPORT,
            created_by="admin_1",
        )
    except Exception as exc:  # ponytail: FastAPI HTTPException is enough until domain errors exist
        assert getattr(exc, "status_code", None) == 409
        assert getattr(exc, "detail", None) == "schedule period must be approved before export"
    else:
        raise AssertionError("expected export creation to fail")
