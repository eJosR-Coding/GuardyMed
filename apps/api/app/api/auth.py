from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from uuid import uuid4

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select

from apps.api.app.core.config import settings
from apps.api.app.infra.db import SessionRow, UserRow, session_scope
from apps.api.app.domain.scheduling.bootstrap import session_factory


class UserRole(StrEnum):
    COORDINATOR = "coordinator"
    WORKER = "worker"
    APPROVER = "approver"


@dataclass(slots=True)
class AuthContext:
    user_id: str
    email: str
    full_name: str
    role: UserRole
    worker_id: str | None = None
    department_id: str | None = None


@dataclass(slots=True)
class SessionUser:
    id: str
    email: str
    full_name: str
    password_hash: str
    role: UserRole
    worker_id: str | None
    department_id: str | None
    is_active: bool


def hash_password(password: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        settings.password_salt.encode("utf-8"),
        200_000,
    )
    return digest.hex()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def build_auth_context(user: SessionUser) -> AuthContext:
    return AuthContext(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        worker_id=user.worker_id,
        department_id=user.department_id,
    )


def get_user_by_email(email: str) -> SessionUser | None:
    normalized = email.strip().lower()
    with session_scope(session_factory) as session:
        row = session.scalar(select(UserRow).where(UserRow.email == normalized))
        return None if row is None else _session_user_from_row(row)


def get_user_by_id(user_id: str) -> SessionUser | None:
    with session_scope(session_factory) as session:
        row = session.get(UserRow, user_id)
        return None if row is None else _session_user_from_row(row)


def create_user(
    *,
    email: str,
    full_name: str,
    password: str,
    role: UserRole,
    worker_id: str | None = None,
    department_id: str | None = None,
) -> SessionUser:
    normalized_email = email.strip().lower()
    normalized_name = full_name.strip()
    existing = get_user_by_email(normalized_email)
    if existing is not None:
        password_hash = hash_password(password)
        with session_scope(session_factory) as session:
            row = session.get(UserRow, existing.id)
            if row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user unavailable")
            row.full_name = normalized_name
            row.password_hash = password_hash
            row.role = role
            row.worker_id = worker_id
            row.department_id = department_id
            row.is_active = "true"
        return SessionUser(
            id=existing.id,
            email=normalized_email,
            full_name=normalized_name,
            password_hash=password_hash,
            role=role,
            worker_id=worker_id,
            department_id=department_id,
            is_active=True,
        )
    user_id = f"usr_{uuid4().hex[:8]}"
    password_hash = hash_password(password)
    row = UserRow(
        id=user_id,
        email=normalized_email,
        full_name=normalized_name,
        password_hash=password_hash,
        role=role,
        worker_id=worker_id,
        department_id=department_id,
        is_active="true",
    )
    with session_scope(session_factory) as session:
        session.add(row)
    return SessionUser(
        id=user_id,
        email=normalized_email,
        full_name=normalized_name,
        password_hash=password_hash,
        role=role,
        worker_id=worker_id,
        department_id=department_id,
        is_active=True,
    )


def create_session_for_user(user: SessionUser) -> str:
    session_id = f"ses_{uuid4().hex}"
    now = datetime.now(timezone.utc)
    row = SessionRow(
        id=session_id,
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
    )
    with session_scope(session_factory) as session:
        session.add(row)
    return session_id


def delete_session(session_id: str) -> None:
    with session_scope(session_factory) as session:
        row = session.get(SessionRow, session_id)
        if row is not None:
            session.delete(row)


def resolve_auth_context(*, session_id: str | None) -> AuthContext:
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing session")
    with session_scope(session_factory) as session:
        row = session.get(SessionRow, session_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
        expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            session.delete(row)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session expired")
        user_row = session.get(UserRow, row.user_id)
        if user_row is None or user_row.is_active != "true":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user unavailable")
        user = _session_user_from_row(user_row)
    return build_auth_context(user)


async def get_auth_context(
    session_id: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> AuthContext:
    return resolve_auth_context(session_id=session_id)


def require_roles(*allowed_roles: UserRole):
    async def guard(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if auth.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return auth

    return guard


def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path="/")


def _session_user_from_row(row: UserRow) -> SessionUser:
    return SessionUser(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        password_hash=row.password_hash,
        role=UserRole(row.role),
        worker_id=row.worker_id,
        department_id=row.department_id,
        is_active=row.is_active == "true",
    )
