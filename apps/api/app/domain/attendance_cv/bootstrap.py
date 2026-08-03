from apps.api.app.core.config import settings
from apps.api.app.domain.attendance_cv.repository import SQLAlchemyAttendanceCVRepository
from apps.api.app.domain.attendance_cv.runtime import DeterministicFaceEmbeddingRuntime, InsightFaceEmbeddingRuntime
from apps.api.app.domain.attendance_cv.service import AttendanceCVService
from apps.api.app.domain.attendance_cv.workflow import AttendanceCVWorkflow
from apps.api.app.domain.scheduling.bootstrap import session_factory


def build_runtime():
    if settings.attendance_cv_runtime == "insightface":
        try:
            return InsightFaceEmbeddingRuntime(model_name=settings.attendance_cv_model_name)
        except Exception:
            return DeterministicFaceEmbeddingRuntime()
    return DeterministicFaceEmbeddingRuntime()


repository = SQLAlchemyAttendanceCVRepository(session_factory)
cv_service = AttendanceCVService(
    runtime=build_runtime(),
    threshold_accept=settings.attendance_cv_accept_threshold,
    threshold_review=settings.attendance_cv_review_threshold,
)
workflow = AttendanceCVWorkflow(repository=repository, cv_service=cv_service)
