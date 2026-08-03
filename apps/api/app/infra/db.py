from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, String, Text, Time, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class DepartmentRow(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(64))


class WorkerRow(Base):
    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    document_id: Mapped[str] = mapped_column(String(64))
    worker_type: Mapped[str] = mapped_column(String(64))
    department_id: Mapped[str] = mapped_column(String(64))


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32))
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[str] = mapped_column(String(8), default="true")


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SchedulePeriodRow(Base):
    __tablename__ = "schedule_periods"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    year: Mapped[int]
    month: Mapped[int]
    department_id: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32))


class ShiftAssignmentRow(Base):
    __tablename__ = "shift_assignments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    schedule_period_id: Mapped[str] = mapped_column(String(64))
    worker_id: Mapped[str] = mapped_column(String(64))
    assignment_type: Mapped[str] = mapped_column(String(32))
    shift_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChangeRequestRow(Base):
    __tablename__ = "change_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(String(64))
    requested_by: Mapped[str] = mapped_column(String(64))
    request_type: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    replacement_worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ApprovalDecisionRow(Base):
    __tablename__ = "approval_decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target_type: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(32))
    decided_by: Mapped[str] = mapped_column(String(64))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(128))
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExportJobRow(Base):
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    schedule_period_id: Mapped[str] = mapped_column(String(64))
    export_type: Mapped[str] = mapped_column(String(32))
    created_by: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AttendanceEnrollmentRow(Base):
    __tablename__ = "attendance_enrollments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    worker_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AttendanceAttemptRow(Base):
    __tablename__ = "attendance_attempts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    worker_id: Mapped[str] = mapped_column(String(64))
    assignment_id: Mapped[str] = mapped_column(String(64))
    attempt_type: Mapped[str] = mapped_column(String(32))
    evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decision_status: Mapped[str] = mapped_column(String(32))
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FaceEnrollmentRow(Base):
    __tablename__ = "face_enrollments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    worker_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FaceTemplateRow(Base):
    __tablename__ = "face_templates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    enrollment_id: Mapped[str] = mapped_column(String(64))
    embedding_json: Mapped[str] = mapped_column(Text)
    quality_score: Mapped[float]
    detector_name: Mapped[str] = mapped_column(String(128))
    model_name: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AttendanceMatchResultRow(Base):
    __tablename__ = "attendance_match_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(64))
    enrollment_id: Mapped[str] = mapped_column(String(64))
    similarity_score: Mapped[float]
    route: Mapped[str] = mapped_column(String(32))
    threshold_accept: Mapped[float]
    threshold_review: Mapped[float]
    detector_name: Mapped[str] = mapped_column(String(128))
    model_name: Mapped[str] = mapped_column(String(128))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def make_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, connect_args=connect_args)


def make_session_factory(database_url: str):
    engine = make_engine(database_url)
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


@contextmanager
def session_scope(session_factory):
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
