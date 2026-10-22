"""Deterministic demo data: one department, five workers, a closed-out previous month and a draft current month.

Dates are relative to ``today`` so the demo always looks current. The module only talks to the
scheduling service, so it works with any repository backend.
"""

from __future__ import annotations

import calendar
from datetime import date, time
from typing import TYPE_CHECKING

from apps.api.app.domain.scheduling.entities import (
    ApprovalDecisionType,
    ApprovalTargetType,
    AssignmentType,
    AttendanceAttemptType,
    ChangeRequestType,
    SchedulePeriodStatus,
    Worker,
)

if TYPE_CHECKING:
    from apps.api.app.domain.scheduling.service import SchedulingService

DEMO_ACTOR_ID = "demo_seed"
DEMO_WORKERS = (
    ("Ana Ruiz", "10010010", "Nurse"),
    ("Luis Torres", "20020020", "Doctor"),
    ("Marta Vega", "30030030", "Nurse"),
    ("Diego Salas", "40040040", "Technician"),
    ("Rosa Quispe", "50050050", "Nurse"),
)
DEMO_LOGIN_WORKER = "Ana Ruiz"


def _previous_month(today: date) -> tuple[int, int]:
    return (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)


def _rota(service: SchedulingService, *, period_id: str, year: int, month: int, workers: list[Worker], anchor_day: int) -> None:
    """Two shifts per day (day + night) rotating over the team; worker 0 is on the day shift on ``anchor_day``."""
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        offset = (day - anchor_day) % len(workers)
        service.create_assignment(
            period_id=period_id,
            worker_id=workers[offset].id,
            assignment_type=AssignmentType.GUARD_SHIFT,
            shift_date=date(year, month, day),
            start_time=time(8, 0),
            end_time=time(20, 0),
            notes="Day coverage",
            actor_id=DEMO_ACTOR_ID,
        )
        service.create_assignment(
            period_id=period_id,
            worker_id=workers[(offset + 1) % len(workers)].id,
            assignment_type=AssignmentType.SHIFT_LEAD if day % 7 == 0 else AssignmentType.ON_CALL,
            shift_date=date(year, month, day),
            start_time=time(20, 0),
            end_time=time(23, 59),
            notes="Night coverage",
            actor_id=DEMO_ACTOR_ID,
        )


def seed(service: SchedulingService, today: date | None = None) -> dict[str, int | bool]:
    today = today or date.today()
    if service.repository.list_departments():
        return summary(service, seeded=False)

    department = service.create_department(name="Emergency", code="ER", actor_id=DEMO_ACTOR_ID)
    workers = [
        service.create_worker(
            full_name=name,
            document_id=document_id,
            worker_type=worker_type,
            department_id=department.id,
            actor_id=DEMO_ACTOR_ID,
        )
        for name, document_id, worker_type in DEMO_WORKERS
    ]

    # Previous month: fully approved, ready to export.
    prev_year, prev_month = _previous_month(today)
    previous = service.create_period(year=prev_year, month=prev_month, department_id=department.id, created_by=DEMO_ACTOR_ID)
    _rota(service, period_id=previous.id, year=prev_year, month=prev_month, workers=workers, anchor_day=1)
    service.update_period_status(previous.id, status_value=SchedulePeriodStatus.IN_REVIEW, actor_id=DEMO_ACTOR_ID)
    service.create_approval_decision(
        target_type=ApprovalTargetType.SCHEDULE_PERIOD,
        target_id=previous.id,
        decision=ApprovalDecisionType.APPROVED,
        decided_by=DEMO_ACTOR_ID,
        comment="Approved for the demo",
    )

    # Current month: still a draft. Ana (the demo worker login) is on the day shift today.
    current = service.create_period(year=today.year, month=today.month, department_id=department.id, created_by=DEMO_ACTOR_ID)
    _rota(service, period_id=current.id, year=today.year, month=today.month, workers=workers, anchor_day=today.day)

    ana, marta = workers[0], workers[2]
    ana_shifts = sorted(
        (item for item in service.repository.list_assignments_for_period(current.id) if item.worker_id == ana.id),
        key=lambda item: item.shift_date,
    )
    upcoming = next((item for item in ana_shifts if item.shift_date > today), ana_shifts[-1])
    service.create_change_request(
        assignment_id=upcoming.id,
        requested_by=ana.id,
        request_type=ChangeRequestType.REPLACEMENT,
        reason="Medical appointment overlaps this shift",
        replacement_worker_id=marta.id,
    )

    # One attendance attempt waiting for review (manual evidence, no face match).
    service.create_attendance_enrollment(worker_id=marta.id, created_by=DEMO_ACTOR_ID)
    marta_shift = next(item for item in service.repository.list_assignments_for_period(current.id) if item.worker_id == marta.id)
    service.create_attendance_enrollment(worker_id=ana.id, created_by=DEMO_ACTOR_ID)
    service.create_attendance_attempt(
        worker_id=marta.id,
        assignment_id=marta_shift.id,
        attempt_type=AttendanceAttemptType.CHECK_IN,
        evidence_ref="manual://front-desk-note",
    )
    return summary(service, seeded=True)


def summary(service: SchedulingService, *, seeded: bool) -> dict[str, int | bool]:
    periods = service.repository.list_periods()
    return {
        "seeded": seeded,
        "departments": len(service.repository.list_departments()),
        "workers": len(service.repository.list_workers()),
        "periods": len(periods),
        "assignments": sum(len(service.repository.list_assignments_for_period(item.id)) for item in periods),
        "change_requests": len(service.repository.list_change_requests()),
    }
