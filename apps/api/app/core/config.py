from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _read_version() -> str:
    try:
        return (_REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


class Settings(BaseSettings):
    """Runtime configuration. Every field can be overridden with a GUARDYMED_* env var."""

    app_name: str = "GuardyMed API"
    app_version: str = _read_version()
    environment: str = "development"
    database_url: str = "sqlite+pysqlite:///./guardymed.db"
    persistence_backend: str = "sqlalchemy"
    session_cookie_name: str = "guardymed_session"
    session_ttl_hours: int = 12
    # Set to true when serving over HTTPS so the session cookie is never sent in clear text.
    session_cookie_secure: bool = False
    # Demo endpoints (public bootstrap of demo accounts) are disabled when this is false.
    demo_mode: bool = True
    # "stub" (default, no ML dependencies) or "insightface" (needs the `cv` extra and model weights).
    attendance_cv_runtime: str = "stub"
    attendance_cv_model_name: str = "buffalo_l"
    # Cosine-similarity routing thresholds. Defaults are calibrated for the InsightFace
    # buffalo_l model (see docs/AI_SERVICES.md); the stub runtime ignores them semantically.
    attendance_cv_accept_threshold: float = 0.45
    attendance_cv_review_threshold: float = 0.30
    attendance_cv_min_quality: float = 0.5

    model_config = SettingsConfigDict(env_prefix="GUARDYMED_", extra="ignore")


settings = Settings()
