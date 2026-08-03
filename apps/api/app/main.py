from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from apps.api.app.api.routes.auth import router as auth_router
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
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(scheduling_router, prefix="/api/v1")
    web_dir = Path(__file__).resolve().parents[2] / "web"
    if web_dir.exists():
        app.mount("/app", StaticFiles(directory=web_dir, html=True), name="web")

        @app.get("/", include_in_schema=False)
        async def root() -> RedirectResponse:
            return RedirectResponse(url="/app")

    return app


app = create_app()
