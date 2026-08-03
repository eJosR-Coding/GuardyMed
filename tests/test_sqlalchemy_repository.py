from datetime import date, time

from apps.api.app.domain.scheduling.entities import (
    ApprovalDecisionType,
    ApprovalTargetType,
    AssignmentType,
    ChangeRequestType,
    ExportType,
    SchedulePeriodStatus,
)
from apps.api.app.domain.scheduling.service import SchedulingService
from apps.api.app.domain.scheduling.sqlalchemy_repository import SQLAlchemySchedulingRepository
from apps.api.app.infra.db import init_db, make_session_factory


def build_service(database_url: str) -> SchedulingService:
    engine, session_factory = make_session_factory(database_url)
    init_db(engine)
    repository = SQLAlchemySchedulingRepository(session_factory)
    return SchedulingService(repository)


def test_sqlalchemy_repository_persists_phase_a_flow(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'guardymed-test.db'}"
    service = build_service(database_url)

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
        created_by="manager_1",
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
    service.update_period_status(period.id, status_value=SchedulePeriodStatus.IN_REVIEW)
    service.create_approval_decision(
        target_type=ApprovalTargetType.SCHEDULE_PERIOD,
        target_id=period.id,
        decision=ApprovalDecisionType.APPROVED,
        decided_by="manager_1",
        comment="approved",
    )
    export_job = service.create_export(
        period_id=period.id,
        export_type=ExportType.OPERATIONAL_SUMMARY,
        created_by="admin_1",
    )

    loaded_period = service.get_period(period.id)
    loaded_assignment = service.get_assignment(assignment.id)
    loaded_request = service.get_change_request(change_request.id)
    loaded_export = service.get_export(export_job.id)
    events = service.list_audit_events(entity_type="export_job", entity_id=export_job.id)

    assert loaded_period.status == SchedulePeriodStatus.APPROVED
    assert loaded_assignment is not None
    assert loaded_request.reason == "Need a swap"
    assert loaded_export.export_type == ExportType.OPERATIONAL_SUMMARY
    assert any(event.action == "export.created" for event in events)
