from __future__ import annotations

from dataclasses import dataclass

from apps.api.app.core.config import settings
from apps.api.app.domain.attendance_cv.repository import SQLAlchemyAttendanceCVRepository
from apps.api.app.domain.attendance_cv.runtime import DeterministicFaceEmbeddingRuntime, InsightFaceEmbeddingRuntime
from apps.api.app.domain.attendance_cv.service import AttendanceCVService
from apps.api.app.domain.attendance_cv.workflow import AttendanceCVWorkflow
from apps.api.app.domain.scheduling.bootstrap import session_factory


@dataclass(frozen=True, slots=True)
class RuntimeSelection:
    runtime: object
    requested: str
    # Set when the requested runtime could not start and the demo stub is used instead.
    fallback_reason: str | None = None


def build_runtime() -> RuntimeSelection:
    requested = settings.attendance_cv_runtime
    if requested == "insightface":
        try:
            runtime = InsightFaceEmbeddingRuntime(
                model_name=settings.attendance_cv_model_name,
                min_quality=settings.attendance_cv_min_quality,
            )
            return RuntimeSelection(runtime=runtime, requested=requested)
        except Exception as exc:  # model download blocked, missing extra, unsupported platform...
            return RuntimeSelection(
                runtime=DeterministicFaceEmbeddingRuntime(),
                requested=requested,
                fallback_reason=f"{type(exc).__name__}: {exc}",
            )
    return RuntimeSelection(runtime=DeterministicFaceEmbeddingRuntime(), requested=requested)


runtime_selection = build_runtime()
repository = SQLAlchemyAttendanceCVRepository(session_factory)
cv_service = AttendanceCVService(
    runtime=runtime_selection.runtime,
    threshold_accept=settings.attendance_cv_accept_threshold,
    threshold_review=settings.attendance_cv_review_threshold,
)
workflow = AttendanceCVWorkflow(repository=repository, cv_service=cv_service)


def runtime_status() -> dict[str, object]:
    runtime = runtime_selection.runtime
    return {
        "runtime": runtime.kind,
        "requested_runtime": runtime_selection.requested,
        "is_demo": runtime.is_demo,
        "fallback_reason": runtime_selection.fallback_reason,
        "model_name": runtime.model_name,
        "detector_name": runtime.detector_name,
        "threshold_accept": cv_service.threshold_accept,
        "threshold_review": cv_service.threshold_review,
    }


def ensure_demo_face_enrollment(worker_id: str, *, created_by: str = "demo_seed") -> bool:
    """Enroll ``worker_id`` with a simulated reference photo so the demo works without a camera.

    Only does anything on the demo runtime; with a real runtime a manager enrolls a real photo.
    """
    import base64

    from apps.api.app.domain.attendance_cv.runtime import demo_capture

    if not runtime_selection.runtime.is_demo or workflow.has_face_template(worker_id):
        return False
    payload = base64.b64encode(demo_capture(worker_id, 1.0)).decode("ascii")
    workflow.create_enrollment(worker_id=worker_id, created_by=created_by, media_base64=payload)
    return True
