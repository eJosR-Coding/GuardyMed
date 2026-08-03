from fastapi import HTTPException

from apps.api.app.api.auth import (
    UserRole,
    build_auth_context,
    create_session_for_user,
    create_user,
    get_user_by_email,
    hash_password,
    resolve_auth_context,
    verify_password,
)
from apps.api.app.main import app


def ensure_demo_user():
    return create_user(
        email="manager@guardymed.local",
        full_name="Demo Manager",
        password="password123",
        role=UserRole.MANAGER,
        department_id="dep_demo",
    )


def test_password_hash_and_verify() -> None:
    password_hash = hash_password("password123")

    assert verify_password("password123", password_hash) is True
    assert verify_password("wrong-pass", password_hash) is False


def test_create_and_fetch_user() -> None:
    user = ensure_demo_user()
    fetched = get_user_by_email("manager@guardymed.local")

    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.role == UserRole.MANAGER


def test_create_user_updates_existing_demo_links() -> None:
    first = create_user(
        email="worker@guardymed.local",
        full_name="Old Worker",
        password="password123",
        role=UserRole.WORKER,
        worker_id="wrk_old",
        department_id="dep_old",
    )

    updated = create_user(
        email="worker@guardymed.local",
        full_name="Ana Ruiz",
        password="password123",
        role=UserRole.WORKER,
        worker_id="wrk_new",
        department_id="dep_new",
    )

    fetched = get_user_by_email("worker@guardymed.local")

    assert updated.id == first.id
    assert fetched is not None
    assert fetched.full_name == "Ana Ruiz"
    assert fetched.worker_id == "wrk_new"
    assert fetched.department_id == "dep_new"


def test_session_context_resolves_from_session_id() -> None:
    user = ensure_demo_user()
    session_id = create_session_for_user(user)

    auth = resolve_auth_context(session_id=session_id)

    assert auth.user_id == user.id
    assert auth.email == "manager@guardymed.local"
    assert auth.role == UserRole.MANAGER


def test_missing_session_is_rejected() -> None:
    try:
        resolve_auth_context(session_id=None)
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "missing session"
    else:
        raise AssertionError("expected missing session to fail")


def test_invalid_session_is_rejected() -> None:
    try:
        resolve_auth_context(session_id="ses_missing")
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "invalid session"
    else:
        raise AssertionError("expected invalid session to fail")


def test_auth_and_app_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/api/v1/auth/bootstrap-demo" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/auth/session" in paths
    assert "/api/v1/scheduling/departments" in paths
    assert "/api/v1/scheduling/review-queue" in paths
    assert "/api/v1/scheduling/attendance/enrollments" in paths
    assert "/api/v1/scheduling/attendance/attempts" in paths
    assert "/app" in paths
    assert "/" in paths
