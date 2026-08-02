from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GuardyMed API"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "sqlite+pysqlite:///./guardymed.db"
    persistence_backend: str = "sqlalchemy"

    model_config = SettingsConfigDict(env_prefix="GUARDYMED_", extra="ignore")


settings = Settings()
