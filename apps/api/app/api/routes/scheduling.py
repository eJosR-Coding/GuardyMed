from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.app.api.auth import AuthContext, UserRole, can_access_department, get_auth_context, is_org_wide, require_roles
from apps.api.app.api.routes.scheduling_models import (
    ApprovalDecisionCreate,
    ApprovalDecisionRead,
    AttendanceAttemptCreate,
    AttendanceAttemptDecisionUpdate,
    AttendanceAttemptRead,
    AttendanceMatchResultRead,
    AttendanceEnrollmentCreate,
    AttendanceEnrollmentRead,
    AuditEventRead,
    DemoCaptureRead,
    FaceRuntimeStatusRead,
    ColleagueRead,
    ChangeRequestCreate,
    ChangeRequestListRead,
    ChangeRequestRead,
    ChangeRequestStatus,
    ChangeRequestUpdate,
    DemoSeedRead,
    DepartmentCreate,
    DepartmentRead,
    ExportCreate,
    ExportRead,
    FaceEnrollmentBundleRead,
    FaceEnrollmentCreate,
    FaceEnrollmentRead,
    FaceTemplateRead,
    FaceVerificationCreate,
    FaceVerificationRead,
    ScheduleCalendarRead,
    SchedulePeriodCreate,
    SchedulePeriodListRead,
    SchedulePeriodRead,
    SchedulePeriodUpdate,
    ReviewQueueRead,
    ShiftAssignmentCreate,
    ShiftAssignmentListRead,
    ShiftAssignmentRead,
    ShiftAssignmentUpdate,
    WorkerCreate,
    WorkerRead,
)
from apps.api.app.domain.attendance_cv.bootstrap import runtime_status as attendance_cv_runtime_status
from apps.api.app.domain.attendance_cv.bootstrap import workflow as attendance_cv_workflow
from apps.api.app.domain.attendance_cv.runtime import demo_capture
from apps.api.app.core.config import settings
from apps.api.app.core.errors import ApiError
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


@router.get("/attendance/capabilities")
async def attendance_capabilities() -> dict[str, object]:
    return {
        "phase": "phase-1-cv-scaffold",
        "modules": ["enrollments", "attempts", "manual-review", "face-enrollment", "face-verification"],
    }


@router.get("/attendance/cv/status", response_model=FaceRuntimeStatusRead)
async def face_runtime_status(
    worker_id: str | None = None,
    auth: AuthContext = Depends(get_auth_context),
) -> FaceRuntimeStatusRead:
    """Which recognition runtime is active (real or demo), its thresholds, and enrolment state for one worker."""
    if auth.role == UserRole.WORKER:
        worker_id = _require_worker_identity(auth)
    elif worker_id is not None:
        _require_department_access(auth, _worker_department_id(worker_id))
    info = attendance_cv_runtime_status()
    captures: list[DemoCaptureRead] = []
    if info["is_demo"] and worker_id is not None:
        captures = _demo_captures(worker_id, accept=float(info["threshold_accept"]), review=float(info["threshold_review"]))
    return FaceRuntimeStatusRead(
        **info,
        worker_id=worker_id,
        enrolled=bool(worker_id) and attendance_cv_workflow.has_face_template(worker_id),
        demo_captures=captures,
    )


@router.get("/attendance/cv/enrollments", response_model=list[FaceTemplateRead])
async def list_face_templates(
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> list[FaceTemplateRead]:
    """Latest face template (metadata only, never the embedding) for each worker the manager can see."""
    templates = []
    for worker in service.list_workers():
        if not can_access_department(auth, worker.department_id):
            continue
        template = attendance_cv_workflow.repository.get_latest_template_for_worker(worker.id)
        if template is not None:
            templates.append(FaceTemplateRead.model_validate(template))
    return templates


@router.post("/demo/seed", response_model=DemoSeedRead)
async def seed_demo_data(
    _: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> DemoSeedRead:
    if not settings.demo_mode:
        raise ApiError(status.HTTP_404_NOT_FOUND, "demo mode is disabled", code="not_found")
    return DemoSeedRead.model_validate(service.seed_demo_data())


@router.post("/attendance/enrollments", response_model=AttendanceEnrollmentRead, status_code=status.HTTP_201_CREATED)
async def create_attendance_enrollment(
    payload: AttendanceEnrollmentCreate,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> AttendanceEnrollmentRead:
    worker = service._require_worker(payload.worker_id)
    _require_department_access(auth, worker.department_id)
    enrollment = service.create_attendance_enrollment(worker_id=payload.worker_id, created_by=auth.user_id)
    return AttendanceEnrollmentRead.model_validate(enrollment)


@router.get("/attendance/enrollments", response_model=list[AttendanceEnrollmentRead])
async def list_attendance_enrollments(
    auth: AuthContext = Depends(get_auth_context),
) -> list[AttendanceEnrollmentRead]:
    worker_id = _require_worker_identity(auth) if auth.role == UserRole.WORKER else None
    items = service.list_attendance_enrollments(worker_id=worker_id)
    if auth.role == UserRole.MANAGER:
        items = [item for item in items if can_access_department(auth, _worker_department_id(item.worker_id))]
    return [AttendanceEnrollmentRead.model_validate(item) for item in items]


@router.post("/attendance/cv/enrollments", response_model=FaceEnrollmentBundleRead, status_code=status.HTTP_201_CREATED)
async def create_face_enrollment(
    payload: FaceEnrollmentCreate,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> FaceEnrollmentBundleRead:
    worker = service._require_worker(payload.worker_id)
    _require_department_access(auth, worker.department_id)
    enrollment, template = attendance_cv_workflow.create_enrollment(
        worker_id=payload.worker_id,
        created_by=auth.user_id,
        media_base64=payload.media_base64,
    )
    return FaceEnrollmentBundleRead(
        enrollment=FaceEnrollmentRead.model_validate(enrollment),
        template=FaceTemplateRead.model_validate(template),
    )


@router.post("/attendance/attempts", response_model=AttendanceAttemptRead, status_code=status.HTTP_201_CREATED)
async def create_attendance_attempt(
    payload: AttendanceAttemptCreate,
    auth: AuthContext = Depends(require_roles(UserRole.WORKER)),
) -> AttendanceAttemptRead:
    worker_id = _require_worker_identity(auth)
    attempt = service.create_attendance_attempt(
        worker_id=worker_id,
        assignment_id=payload.assignment_id,
        attempt_type=payload.attempt_type,
        evidence_ref=payload.evidence_ref,
    )
    return AttendanceAttemptRead.model_validate(attempt)


@router.post("/attendance/cv/attempts", response_model=FaceVerificationRead, status_code=status.HTTP_201_CREATED)
async def create_face_verification_attempt(
    payload: FaceVerificationCreate,
    auth: AuthContext = Depends(require_roles(UserRole.WORKER)),
) -> FaceVerificationRead:
    worker_id = _require_worker_identity(auth)
    attempt, match_result = attendance_cv_workflow.verify_assignment_attempt(
        worker_id=worker_id,
        assignment_id=payload.assignment_id,
        attempt_type=payload.attempt_type,
        media_base64=payload.media_base64,
    )
    return FaceVerificationRead(
        attempt=AttendanceAttemptRead.model_validate(attempt),
        match_result=AttendanceMatchResultRead.model_validate(match_result),
    )


@router.get("/attendance/cv/attempts/{attempt_id}/match-result", response_model=AttendanceMatchResultRead)
async def get_face_verification_match_result(
    attempt_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> AttendanceMatchResultRead:
    attempt = service.get_attendance_attempt(attempt_id)
    if auth.role == UserRole.WORKER and attempt.worker_id != _require_worker_identity(auth):
        raise _forbidden("worker can only access own attendance evidence")
    if auth.role == UserRole.MANAGER:
        period = service.get_period(service.get_assignment(attempt.assignment_id).schedule_period_id)
        _require_department_access(auth, period.department_id)
    result = attendance_cv_workflow.get_match_result(attempt_id)
    return AttendanceMatchResultRead.model_validate(result)


@router.get("/attendance/attempts", response_model=list[AttendanceAttemptRead])
async def list_attendance_attempts(
    auth: AuthContext = Depends(get_auth_context),
) -> list[AttendanceAttemptRead]:
    if auth.role == UserRole.WORKER:
        items = service.list_attendance_attempts(worker_id=_require_worker_identity(auth))
    else:
        items = [
            item
            for item in service.list_attendance_attempts()
            if can_access_department(auth, _worker_department_id(item.worker_id))
        ]
    return [AttendanceAttemptRead.model_validate(item) for item in items]


@router.get("/attendance/review-queue", response_model=list[AttendanceAttemptRead])
async def list_attendance_review_queue(
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> list[AttendanceAttemptRead]:
    items = [
        item
        for item in service.list_attendance_attempts(pending_only=True)
        if can_access_department(auth, _worker_department_id(item.worker_id))
    ]
    return [AttendanceAttemptRead.model_validate(item) for item in items]


@router.patch("/attendance/attempts/{attempt_id}", response_model=AttendanceAttemptRead)
async def review_attendance_attempt(
    attempt_id: str,
    payload: AttendanceAttemptDecisionUpdate,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> AttendanceAttemptRead:
    attempt = service.get_attendance_attempt(attempt_id)
    period = service.get_period(service.get_assignment(attempt.assignment_id).schedule_period_id)
    _require_department_access(auth, period.department_id)
    updated = service.review_attendance_attempt(
        attempt_id,
        decision_status=payload.decision_status,
        decided_by=auth.user_id,
        review_reason=payload.review_reason,
    )
    return AttendanceAttemptRead.model_validate(updated)


@router.post("/departments", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentCreate,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> DepartmentRead:
    if not is_org_wide(auth):
        raise _forbidden("only organisation-wide managers can create departments")
    department = service.create_department(name=payload.name, code=payload.code, actor_id=auth.user_id)
    return DepartmentRead.model_validate(department)


@router.get("/departments", response_model=list[DepartmentRead])
async def list_departments(
    auth: AuthContext = Depends(get_auth_context),
) -> list[DepartmentRead]:
    items = [item for item in service.list_departments() if can_access_department(auth, item.id)]
    return [DepartmentRead.model_validate(item) for item in items]


@router.post("/workers", response_model=WorkerRead, status_code=status.HTTP_201_CREATED)
async def create_worker(
    payload: WorkerCreate,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> WorkerRead:
    _require_department_access(auth, payload.department_id)
    worker = service.create_worker(
        full_name=payload.full_name,
        document_id=payload.document_id,
        worker_type=payload.worker_type,
        department_id=payload.department_id,
        actor_id=auth.user_id,
    )
    return WorkerRead.model_validate(worker)


@router.get("/workers", response_model=list[WorkerRead])
async def list_workers(
    department_id: str | None = None,
    auth: AuthContext = Depends(get_auth_context),
) -> list[WorkerRead]:
    if auth.role == UserRole.WORKER:
        worker_id = _require_worker_identity(auth)
        worker = next(item for item in service.list_workers() if item.id == worker_id)
        return [WorkerRead.model_validate(worker)]
    if department_id is not None:
        _require_department_access(auth, department_id)
    effective_department_id = department_id or auth.department_id
    items = service.list_workers(department_id=effective_department_id)
    return [WorkerRead.model_validate(item) for item in items]


@router.get("/colleagues", response_model=list[ColleagueRead])
async def list_colleagues(
    auth: AuthContext = Depends(require_roles(UserRole.WORKER)),
) -> list[ColleagueRead]:
    """Names of the other workers in the caller's department (no personal documents), for picking a replacement."""
    own_id = _require_worker_identity(auth)
    items = service.list_workers(department_id=auth.department_id) if auth.department_id else []
    return [ColleagueRead.model_validate(item) for item in items if item.id != own_id]


@router.post("/schedule-periods", response_model=SchedulePeriodRead, status_code=status.HTTP_201_CREATED)
async def create_schedule_period(
    payload: SchedulePeriodCreate,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> SchedulePeriodRead:
    _require_department_access(auth, payload.department_id)
    period = service.create_period(
        year=payload.year,
        month=payload.month,
        department_id=payload.department_id,
        created_by=auth.user_id,
    )
    return SchedulePeriodRead.model_validate(period)


@router.get("/schedule-periods", response_model=SchedulePeriodListRead)
async def list_schedule_periods(
    department_id: str | None = None,
    auth: AuthContext = Depends(get_auth_context),
) -> SchedulePeriodListRead:
    if department_id is not None:
        _require_department_access(auth, department_id)
    effective_department_id = department_id or auth.department_id
    return SchedulePeriodListRead(
        items=[SchedulePeriodRead.model_validate(item) for item in service.list_periods(department_id=effective_department_id)]
    )


@router.get("/schedule-periods/{period_id}", response_model=SchedulePeriodRead)
async def get_schedule_period(
    period_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> SchedulePeriodRead:
    period = service.get_period(period_id)
    _require_department_access(auth, period.department_id)
    return SchedulePeriodRead.model_validate(period)


@router.patch("/schedule-periods/{period_id}", response_model=SchedulePeriodRead)
async def update_schedule_period(
    period_id: str,
    payload: SchedulePeriodUpdate,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> SchedulePeriodRead:
    period = service.get_period(period_id)
    _require_department_access(auth, period.department_id)
    updated = service.update_period_status(period_id, status_value=payload.status, actor_id=auth.user_id)
    return SchedulePeriodRead.model_validate(updated)


@router.post(
    "/schedule-periods/{period_id}/assignments",
    response_model=ShiftAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_shift_assignment(
    period_id: str,
    payload: ShiftAssignmentCreate,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> ShiftAssignmentRead:
    period = service.get_period(period_id)
    _require_department_access(auth, period.department_id)
    assignment = service.create_assignment(
        period_id=period_id,
        worker_id=payload.worker_id,
        assignment_type=payload.assignment_type,
        shift_date=payload.shift_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        notes=payload.notes,
        actor_id=auth.user_id,
    )
    return ShiftAssignmentRead.model_validate(assignment)


@router.patch("/assignments/{assignment_id}", response_model=ShiftAssignmentRead)
async def update_shift_assignment(
    assignment_id: str,
    payload: ShiftAssignmentUpdate,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> ShiftAssignmentRead:
    assignment = service.get_assignment(assignment_id)
    period = service.get_period(assignment.schedule_period_id)
    _require_department_access(auth, period.department_id)
    assignment = service.update_assignment(
        assignment_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        notes=payload.notes,
        actor_id=auth.user_id,
    )
    return ShiftAssignmentRead.model_validate(assignment)


@router.get("/schedule-periods/{period_id}/calendar", response_model=ScheduleCalendarRead)
async def get_schedule_calendar(
    period_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> ScheduleCalendarRead:
    period = service.get_period(period_id)
    _require_department_access(auth, period.department_id)
    calendar = service.get_calendar(period_id)
    return ScheduleCalendarRead.model_validate(calendar)


@router.get("/workers/{worker_id}/assignments", response_model=ShiftAssignmentListRead)
async def list_worker_assignments(
    worker_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> ShiftAssignmentListRead:
    _require_worker_access(auth, worker_id)
    if auth.role == UserRole.MANAGER:
        _require_department_access(auth, _worker_department_id(worker_id))
    assignments = service.list_assignments_for_worker(worker_id)
    return ShiftAssignmentListRead(items=[ShiftAssignmentRead.model_validate(item) for item in assignments])


@router.post(
    "/assignments/{assignment_id}/change-requests",
    response_model=ChangeRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_change_request(
    assignment_id: str,
    payload: ChangeRequestCreate,
    auth: AuthContext = Depends(require_roles(UserRole.WORKER)),
) -> ChangeRequestRead:
    worker_id = _require_worker_identity(auth)
    change_request = service.create_change_request(
        assignment_id=assignment_id,
        requested_by=worker_id,
        request_type=payload.request_type,
        reason=payload.reason,
        replacement_worker_id=payload.replacement_worker_id,
    )
    return ChangeRequestRead.model_validate(change_request)


@router.get("/change-requests/{request_id}", response_model=ChangeRequestRead)
async def get_change_request(
    request_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> ChangeRequestRead:
    change_request = service.get_change_request(request_id)
    if auth.role == UserRole.WORKER and change_request.requested_by != _require_worker_identity(auth):
        raise _forbidden()
    if auth.role == UserRole.MANAGER:
        _require_department_access(auth, _change_request_department_id(change_request))
    return ChangeRequestRead.model_validate(change_request)


@router.get("/change-requests", response_model=ChangeRequestListRead)
async def list_change_requests(
    requested_by: str | None = None,
    auth: AuthContext = Depends(get_auth_context),
) -> ChangeRequestListRead:
    effective_requested_by = requested_by
    if auth.role == UserRole.WORKER:
        effective_requested_by = _require_worker_identity(auth)
    requests = service.list_change_requests(requested_by=effective_requested_by)
    if auth.role == UserRole.MANAGER:
        requests = [item for item in requests if can_access_department(auth, _change_request_department_id(item))]
    return ChangeRequestListRead(items=[ChangeRequestRead.model_validate(item) for item in requests])


@router.patch("/change-requests/{request_id}", response_model=ChangeRequestRead)
async def update_change_request(
    request_id: str,
    payload: ChangeRequestUpdate,
    auth: AuthContext = Depends(get_auth_context),
) -> ChangeRequestRead:
    if auth.role != UserRole.WORKER:
        raise _forbidden()
    change_request = service.get_change_request(request_id)
    if change_request.requested_by != _require_worker_identity(auth):
        raise _forbidden()
    if payload.status != ChangeRequestStatus.CANCELLED:
        raise _forbidden("workers may only cancel their own pending requests")
    change_request = service.update_change_request_status(request_id, status_value=payload.status)
    return ChangeRequestRead.model_validate(change_request)


@router.get("/review-queue", response_model=ReviewQueueRead)
async def get_review_queue(
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> ReviewQueueRead:
    queue = service.list_review_queue()
    return ReviewQueueRead.model_validate(
        {
            "schedule_periods": [item for item in queue["schedule_periods"] if can_access_department(auth, item.department_id)],
            "change_requests": [
                item for item in queue["change_requests"] if can_access_department(auth, _change_request_department_id(item))
            ],
        }
    )


@router.post("/approval-decisions", response_model=ApprovalDecisionRead, status_code=status.HTTP_201_CREATED)
async def create_approval_decision(
    payload: ApprovalDecisionCreate,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> ApprovalDecisionRead:
    if payload.target_type == "schedule_period":
        period = service.get_period(payload.target_id)
        _require_department_access(auth, period.department_id)
    elif payload.target_type == "change_request":
        change_request = service.get_change_request(payload.target_id)
        assignment = service.get_assignment(change_request.assignment_id)
        period = service.get_period(assignment.schedule_period_id)
        _require_department_access(auth, period.department_id)
    decision = service.create_approval_decision(
        target_type=payload.target_type,
        target_id=payload.target_id,
        decision=payload.decision,
        decided_by=auth.user_id,
        comment=payload.comment,
    )
    return ApprovalDecisionRead.model_validate(decision)


@router.get("/audit-events", response_model=list[AuditEventRead])
async def list_audit_events(
    entity_type: str | None = None,
    entity_id: str | None = None,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> list[AuditEventRead]:
    events = service.list_audit_events(entity_type=entity_type, entity_id=entity_id)
    visible = [item for item in events if is_org_wide(auth) or _event_department_id(item) in {auth.department_id, None}]
    return [AuditEventRead.model_validate(item) for item in visible]


@router.post("/schedule-periods/{period_id}/exports", response_model=ExportRead, status_code=status.HTTP_201_CREATED)
async def create_export(
    period_id: str,
    payload: ExportCreate,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> ExportRead:
    period = service.get_period(period_id)
    _require_department_access(auth, period.department_id)
    export_job = service.create_export(
        period_id=period_id,
        export_type=payload.export_type,
        created_by=auth.user_id,
    )
    return ExportRead.model_validate(export_job)


@router.get("/schedule-periods/{period_id}/exports", response_model=list[ExportRead])
async def list_exports_for_period(
    period_id: str,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> list[ExportRead]:
    period = service.get_period(period_id)
    _require_department_access(auth, period.department_id)
    exports = service.list_exports_for_period(period_id)
    return [ExportRead.model_validate(item) for item in exports]


@router.get("/exports/{export_id}", response_model=ExportRead)
async def get_export(
    export_id: str,
    auth: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> ExportRead:
    export_job = service.get_export(export_id)
    period = service.get_period(export_job.schedule_period_id)
    _require_department_access(auth, period.department_id)
    return ExportRead.model_validate(export_job)


def _demo_captures(worker_id: str, *, accept: float, review: float) -> list[DemoCaptureRead]:
    """Simulated captures for the demo runtime. They carry no face: the stub reads the requested cosine from the payload."""
    import base64

    def encode(identity: str, cosine: float) -> str:
        return base64.b64encode(demo_capture(identity, cosine)).decode("ascii")

    borderline = round((accept + review) / 2, 4)
    return [
        DemoCaptureRead(id="enroll", label="Reference photo", expected_outcome="verified", media_base64=encode(worker_id, 1.0)),
        DemoCaptureRead(id="clear", label="Clear capture of the same person", expected_outcome="verified", media_base64=encode(worker_id, 0.9)),
        DemoCaptureRead(id="borderline", label="Poor lighting, same person", expected_outcome="needs_review", media_base64=encode(worker_id, borderline)),
        DemoCaptureRead(id="stranger", label="A different person", expected_outcome="not_verified", media_base64=encode("stranger-at-the-door", 1.0)),
    ]


def _require_department_access(auth: AuthContext, department_id: str) -> None:
    if not can_access_department(auth, department_id):
        raise _forbidden("not allowed to access another department")


def _worker_department_id(worker_id: str) -> str:
    return service._require_worker(worker_id).department_id


def _assignment_department_id(assignment_id: str) -> str:
    return service.get_period(service.get_assignment(assignment_id).schedule_period_id).department_id


def _change_request_department_id(change_request) -> str:
    return _assignment_department_id(change_request.assignment_id)


def _event_department_id(event) -> str | None:
    """Best-effort department of an audit event's subject; None when it cannot be resolved (global events)."""
    try:
        if event.entity_type == "department":
            return event.entity_id
        if event.entity_type == "worker":
            return _worker_department_id(event.entity_id)
        if event.entity_type == "schedule_period":
            return service.get_period(event.entity_id).department_id
        if event.entity_type == "assignment":
            return _assignment_department_id(event.entity_id)
        if event.entity_type == "change_request":
            return _change_request_department_id(service.get_change_request(event.entity_id))
        if event.entity_type == "attendance_attempt":
            return _assignment_department_id(service.get_attendance_attempt(event.entity_id).assignment_id)
        if event.entity_type == "attendance_enrollment":
            worker_id = event.payload.get("worker_id")
            return _worker_department_id(str(worker_id)) if worker_id else None
        if event.entity_type == "export_job":
            return service.get_period(str(event.payload.get("schedule_period_id"))).department_id
        if event.entity_type == "approval_decision":
            target_id = str(event.payload.get("target_id"))
            if event.payload.get("target_type") == "schedule_period":
                return service.get_period(target_id).department_id
            return _change_request_department_id(service.get_change_request(target_id))
    except HTTPException:
        return None
    return None


def _require_worker_identity(auth: AuthContext) -> str:
    if not auth.worker_id:
        raise _forbidden("worker identity is not linked")
    return auth.worker_id


def _require_worker_access(auth: AuthContext, worker_id: str) -> None:
    if auth.role == UserRole.WORKER and _require_worker_identity(auth) != worker_id:
        raise _forbidden()


def _forbidden(detail: str = "forbidden") -> HTTPException:
    return ApiError(status.HTTP_403_FORBIDDEN, detail, code="forbidden")
