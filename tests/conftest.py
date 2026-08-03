import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from apps.api.app.api.auth import SessionRow, UserRow, session_factory
from apps.api.app.infra.db import (
    ApprovalDecisionRow,
    AttendanceAttemptRow,
    AttendanceEnrollmentRow,
    AuditEventRow,
    ChangeRequestRow,
    DepartmentRow,
    ExportJobRow,
    SchedulePeriodRow,
    ShiftAssignmentRow,
    WorkerRow,
    session_scope,
)
from apps.api.app.main import app


def reset_database() -> None:
    with session_scope(session_factory) as session:
        session.execute(delete(SessionRow))
        session.execute(delete(UserRow))
        session.execute(delete(ApprovalDecisionRow))
        session.execute(delete(AttendanceAttemptRow))
        session.execute(delete(AttendanceEnrollmentRow))
        session.execute(delete(ChangeRequestRow))
        session.execute(delete(ShiftAssignmentRow))
        session.execute(delete(ExportJobRow))
        session.execute(delete(AuditEventRow))
        session.execute(delete(SchedulePeriodRow))
        session.execute(delete(WorkerRow))
        session.execute(delete(DepartmentRow))


async def login(client: AsyncClient, email: str, password: str = "password123") -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def seed_and_login(client: AsyncClient, email: str) -> dict:
    response = await client.post("/api/v1/auth/bootstrap-demo")
    assert response.status_code == 200, response.text
    return await login(client, email)


async def build_manager_flow(client: AsyncClient) -> dict[str, str]:
    department = await client.post(
        "/api/v1/scheduling/departments",
        json={"name": "Pediatrics", "code": "PED"},
    )
    assert department.status_code == 201, department.text
    department_id = department.json()["id"]

    worker = await client.post(
        "/api/v1/scheduling/workers",
        json={
            "full_name": "Carla Mendez",
            "document_id": "55554444",
            "worker_type": "Nurse",
            "department_id": department_id,
        },
    )
    assert worker.status_code == 201, worker.text
    worker_id = worker.json()["id"]

    period = await client.post(
        "/api/v1/scheduling/schedule-periods",
        json={
            "year": 2026,
            "month": 9,
            "department_id": department_id,
        },
    )
    assert period.status_code == 201, period.text
    period_id = period.json()["id"]

    assignment = await client.post(
        f"/api/v1/scheduling/schedule-periods/{period_id}/assignments",
        json={
            "worker_id": worker_id,
            "assignment_type": "guard_shift",
            "shift_date": "2026-09-03",
            "start_time": "08:00:00",
            "end_time": "20:00:00",
            "notes": "Day coverage",
        },
    )
    assert assignment.status_code == 201, assignment.text
    assignment_id = assignment.json()["id"]

    return {
        "department_id": department_id,
        "worker_id": worker_id,
        "period_id": period_id,
        "assignment_id": assignment_id,
    }


@pytest.fixture
async def client():
    reset_database()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as current:
        yield current
    reset_database()
