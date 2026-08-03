import asyncio

from fastapi import HTTPException

from apps.api.app.api.auth import UserRole, get_auth_context, require_roles, resolve_auth_context
from apps.api.app.main import app


def test_missing_auth_headers_are_rejected() -> None:
    try:
        resolve_auth_context(user_id=None, user_role=None)
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "missing auth headers"
    else:
        raise AssertionError("expected auth context resolution to fail")


def test_invalid_role_is_rejected() -> None:
    try:
        resolve_auth_context(user_id="user_1", user_role="admin")
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "invalid user role"
    else:
        raise AssertionError("expected invalid role to fail")


def test_valid_auth_context_is_built() -> None:
    auth = resolve_auth_context(user_id="coord_1", user_role="coordinator")

    assert auth.user_id == "coord_1"
    assert auth.role == UserRole.COORDINATOR


def test_role_guard_rejects_forbidden_role() -> None:
    guard = require_roles(UserRole.COORDINATOR)
    worker_auth = asyncio.run(get_auth_context(x_user_id="worker_1", x_user_role="worker"))

    try:
        asyncio.run(guard(worker_auth))
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "forbidden"
    else:
        raise AssertionError("expected role guard to fail")


def test_role_guard_accepts_allowed_role() -> None:
    guard = require_roles(UserRole.APPROVER)
    approver_auth = asyncio.run(get_auth_context(x_user_id="approver_1", x_user_role="approver"))

    resolved = asyncio.run(guard(approver_auth))

    assert resolved.user_id == "approver_1"
    assert resolved.role == UserRole.APPROVER


def test_auth_protected_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/api/v1/scheduling/departments" in paths
    assert "/api/v1/scheduling/demo/seed" in paths
    assert "/api/v1/scheduling/workers" in paths
    assert "/api/v1/scheduling/schedule-periods" in paths
    assert "/api/v1/scheduling/change-requests" in paths
    assert "/api/v1/scheduling/review-queue" in paths
    assert "/api/v1/scheduling/approval-decisions" in paths
    assert "/api/v1/scheduling/audit-events" in paths
    assert "/app" in paths
    assert "/" in paths
