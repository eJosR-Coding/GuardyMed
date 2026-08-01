from fastapi import APIRouter, status

from apps.api.app.api.routes.scheduling_models import (
    DepartmentCreate,
    DepartmentRead,
    ScheduleCalendarRead,
    SchedulePeriodCreate,
    SchedulePeriodRead,
    SchedulePeriodUpdate,
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
            "rules",
            "audit",
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
