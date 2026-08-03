from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from dataclasses import asdict

from apps.api.app.api.auth import (
    AuthContext,
    UserRole,
    build_auth_context,
    clear_session_cookie,
    create_session_for_user,
    delete_session,
    get_auth_context,
    get_user_by_email,
    require_roles,
    set_session_cookie,
    verify_password,
)
from apps.api.app.domain.scheduling import service as scheduling_service
from apps.api.app.domain.scheduling.entities import Worker
from apps.api.app.api.auth import create_user


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned:
            raise ValueError("email must be valid")
        return cleaned


class SessionRead(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: UserRole
    worker_id: str | None = None
    department_id: str | None = None


class DemoBootstrapRead(BaseModel):
    seeded: bool
    credentials: list[dict[str, str]]


@router.post("/bootstrap-demo", response_model=DemoBootstrapRead)
async def bootstrap_demo() -> DemoBootstrapRead:
    try:
        seed_result = scheduling_service.seed_demo_data()
    except HTTPException as exc:
        if exc.status_code != 409:
            raise
        periods = scheduling_service.list_periods()
        seed_result = {
            "seeded": False,
            "departments": len(scheduling_service.list_departments()),
            "workers": len(scheduling_service.list_workers()),
            "periods": len(periods),
            "assignments": sum(len(scheduling_service.repository.list_assignments_for_period(item.id)) for item in periods),
            "change_requests": len(scheduling_service.repository.list_change_requests()),
        }
    workers = scheduling_service.list_workers()
    department_id = workers[0].department_id if workers else None
    worker_map = {worker.full_name: worker for worker in workers}
    created_before = get_user_by_email("manager@guardymed.local") is not None

    create_user(
        email="manager@guardymed.local",
        full_name="Demo Manager",
        password="password123",
        role=UserRole.MANAGER,
        department_id=department_id,
    )
    worker = _pick_worker(worker_map)
    create_user(
        email="worker@guardymed.local",
        full_name=worker.full_name,
        password="password123",
        role=UserRole.WORKER,
        worker_id=worker.id,
        department_id=worker.department_id,
    )

    return DemoBootstrapRead(
        seeded=seed_result["seeded"] or not created_before,
        credentials=[
            {"email": "manager@guardymed.local", "password": "password123", "role": "manager"},
            {"email": "worker@guardymed.local", "password": "password123", "role": "worker"},
        ],
    )


@router.post("/login", response_model=SessionRead)
async def login(payload: LoginRequest, response: Response) -> SessionRead:
    user = get_user_by_email(payload.email)
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        clear_session_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    session_id = create_session_for_user(user)
    set_session_cookie(response, session_id)
    return SessionRead.model_validate(asdict(build_auth_context(user)))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session_id: str | None = Cookie(default=None, alias="guardymed_session"),
    auth: AuthContext = Depends(get_auth_context),
) -> Response:
    if session_id:
        delete_session(session_id)
    clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/session", response_model=SessionRead)
async def get_session(
    auth: AuthContext = Depends(get_auth_context),
) -> SessionRead:
    return SessionRead.model_validate(asdict(auth))


@router.get("/users", response_model=list[SessionRead])
async def list_demo_users(
    _: AuthContext = Depends(require_roles(UserRole.MANAGER)),
) -> list[SessionRead]:
    demo_users = [
        get_user_by_email("manager@guardymed.local"),
        get_user_by_email("worker@guardymed.local"),
    ]
    return [SessionRead.model_validate(asdict(build_auth_context(user))) for user in demo_users if user is not None]


def _pick_worker(worker_map: dict[str, Worker]) -> Worker:
    return worker_map.get("Ana Ruiz") or next(iter(worker_map.values()))
