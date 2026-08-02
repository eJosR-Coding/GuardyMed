from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fastapi import Depends, Header, HTTPException, status


class UserRole(StrEnum):
    COORDINATOR = "coordinator"
    WORKER = "worker"
    APPROVER = "approver"


@dataclass(slots=True)
class AuthContext:
    user_id: str
    role: UserRole


def resolve_auth_context(*, user_id: str | None, user_role: str | None) -> AuthContext:
    if not user_id or not user_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing auth headers")
    try:
        role = UserRole(user_role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid user role") from exc
    return AuthContext(user_id=user_id, role=role)


async def get_auth_context(
    x_user_id: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
) -> AuthContext:
    return resolve_auth_context(user_id=x_user_id, user_role=x_user_role)


def require_roles(*allowed_roles: UserRole):
    async def guard(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if auth.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return auth

    return guard
