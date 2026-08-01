from datetime import date, time

from apps.api.app.domain.scheduling.entities import (
    AssignmentType,
    ChangeRequestStatus,
    ChangeRequestType,
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
