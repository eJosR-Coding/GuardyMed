from fastapi import APIRouter, status

from apps.api.app.api.routes.scheduling_models import (
    ApprovalDecisionCreate,
    ApprovalDecisionRead,
    AuditEventRead,
    ChangeRequestCreate,
    ChangeRequestRead,
    ChangeRequestUpdate,
    DepartmentCreate,
    DepartmentRead,
    ExportCreate,
    ExportRead,
    ScheduleCalendarRead,
    SchedulePeriodCreate,
    SchedulePeriodRead,
    SchedulePeriodUpdate,
    ReviewQueueRead,
    ShiftAssignmentCreate,
    ShiftAssignmentRead,
    ShiftAssignmentUpdate,
    WorkerCreate,
    WorkerRead,
)
from apps.api.app.domain.scheduling import service

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


@router.get("/capabilities")
async def scheduling_capabilities() -> dict[str, object]:
    return {
        "phase": "phase-1-core",
        "modules": [
            "periods",
            "services",
            "workers",
            "assignments",
            "requests",
            "approvals",
            "rules",
            "audit",
            "exports",
        ],
    }


@router.post("/departments", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
async def create_department(payload: DepartmentCreate) -> DepartmentRead:
    return DepartmentRead.model_validate(service.create_department(name=payload.name, code=payload.code))


@router.post("/workers", response_model=WorkerRead, status_code=status.HTTP_201_CREATED)
async def create_worker(payload: WorkerCreate) -> WorkerRead:
    worker = service.create_worker(
        full_name=payload.full_name,
        document_id=payload.document_id,
        worker_type=payload.worker_type,
        department_id=payload.department_id,
    )
    return WorkerRead.model_validate(worker)


@router.post("/schedule-periods", response_model=SchedulePeriodRead, status_code=status.HTTP_201_CREATED)
async def create_schedule_period(payload: SchedulePeriodCreate) -> SchedulePeriodRead:
    period = service.create_period(
        year=payload.year,
        month=payload.month,
        department_id=payload.department_id,
        created_by=payload.created_by,
    )
    return SchedulePeriodRead.model_validate(period)


@router.get("/schedule-periods/{period_id}", response_model=SchedulePeriodRead)
async def get_schedule_period(period_id: str) -> SchedulePeriodRead:
    return SchedulePeriodRead.model_validate(service.get_period(period_id))


@router.patch("/schedule-periods/{period_id}", response_model=SchedulePeriodRead)
async def update_schedule_period(period_id: str, payload: SchedulePeriodUpdate) -> SchedulePeriodRead:
    return SchedulePeriodRead.model_validate(service.update_period_status(period_id, status_value=payload.status))


@router.post(
    "/schedule-periods/{period_id}/assignments",
    response_model=ShiftAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_shift_assignment(period_id: str, payload: ShiftAssignmentCreate) -> ShiftAssignmentRead:
    assignment = service.create_assignment(
        period_id=period_id,
        worker_id=payload.worker_id,
        assignment_type=payload.assignment_type,
        shift_date=payload.shift_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        notes=payload.notes,
    )
    return ShiftAssignmentRead.model_validate(assignment)


@router.patch("/assignments/{assignment_id}", response_model=ShiftAssignmentRead)
async def update_shift_assignment(assignment_id: str, payload: ShiftAssignmentUpdate) -> ShiftAssignmentRead:
    assignment = service.update_assignment(
        assignment_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        notes=payload.notes,
    )
    return ShiftAssignmentRead.model_validate(assignment)


@router.get("/schedule-periods/{period_id}/calendar", response_model=ScheduleCalendarRead)
async def get_schedule_calendar(period_id: str) -> ScheduleCalendarRead:
    calendar = service.get_calendar(period_id)
    return ScheduleCalendarRead.model_validate(calendar)


@router.post(
    "/assignments/{assignment_id}/change-requests",
    response_model=ChangeRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_change_request(assignment_id: str, payload: ChangeRequestCreate) -> ChangeRequestRead:
    change_request = service.create_change_request(
        assignment_id=assignment_id,
        requested_by=payload.requested_by,
        request_type=payload.request_type,
        reason=payload.reason,
        replacement_worker_id=payload.replacement_worker_id,
    )
    return ChangeRequestRead.model_validate(change_request)


@router.get("/change-requests/{request_id}", response_model=ChangeRequestRead)
async def get_change_request(request_id: str) -> ChangeRequestRead:
    return ChangeRequestRead.model_validate(service.get_change_request(request_id))


@router.patch("/change-requests/{request_id}", response_model=ChangeRequestRead)
async def update_change_request(request_id: str, payload: ChangeRequestUpdate) -> ChangeRequestRead:
    change_request = service.update_change_request_status(request_id, status_value=payload.status)
    return ChangeRequestRead.model_validate(change_request)


@router.get("/review-queue", response_model=ReviewQueueRead)
async def get_review_queue() -> ReviewQueueRead:
    queue = service.list_review_queue()
    return ReviewQueueRead.model_validate(queue)


@router.post("/approval-decisions", response_model=ApprovalDecisionRead, status_code=status.HTTP_201_CREATED)
async def create_approval_decision(payload: ApprovalDecisionCreate) -> ApprovalDecisionRead:
    decision = service.create_approval_decision(
        target_type=payload.target_type,
        target_id=payload.target_id,
        decision=payload.decision,
        decided_by=payload.decided_by,
        comment=payload.comment,
    )
    return ApprovalDecisionRead.model_validate(decision)


@router.get("/audit-events", response_model=list[AuditEventRead])
async def list_audit_events(entity_type: str | None = None, entity_id: str | None = None) -> list[AuditEventRead]:
    events = service.list_audit_events(entity_type=entity_type, entity_id=entity_id)
    return [AuditEventRead.model_validate(item) for item in events]


@router.post("/schedule-periods/{period_id}/exports", response_model=ExportRead, status_code=status.HTTP_201_CREATED)
async def create_export(period_id: str, payload: ExportCreate) -> ExportRead:
    export_job = service.create_export(
        period_id=period_id,
        export_type=payload.export_type,
        created_by=payload.created_by,
    )
    return ExportRead.model_validate(export_job)


@router.get("/schedule-periods/{period_id}/exports", response_model=list[ExportRead])
async def list_exports_for_period(period_id: str) -> list[ExportRead]:
    exports = service.list_exports_for_period(period_id)
    return [ExportRead.model_validate(item) for item in exports]


@router.get("/exports/{export_id}", response_model=ExportRead)
async def get_export(export_id: str) -> ExportRead:
    return ExportRead.model_validate(service.get_export(export_id))
