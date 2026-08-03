from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GuardyMed API"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "sqlite+pysqlite:///./guardymed.db"
    persistence_backend: str = "sqlalchemy"
    session_cookie_name: str = "guardymed_session"
    session_ttl_hours: int = 12
    password_salt: str = "guardymed-dev-salt"

    model_config = SettingsConfigDict(env_prefix="GUARDYMED_", extra="ignore")


settings = Settings()
