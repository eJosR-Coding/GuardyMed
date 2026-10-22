from fastapi import APIRouter

from apps.api.app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck() -> dict[str, object]:
    return {"status": "ok", "version": settings.app_version, "demo_mode": settings.demo_mode}
