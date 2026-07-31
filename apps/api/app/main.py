from fastapi import FastAPI

from apps.api.app.api.routes.health import router as health_router
from apps.api.app.api.routes.scheduling import router as scheduling_router
from apps.api.app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(health_router)
    app.include_router(scheduling_router, prefix="/api/v1")
    return app


app = create_app()

