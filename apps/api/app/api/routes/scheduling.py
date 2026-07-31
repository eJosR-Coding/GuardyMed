from fastapi import APIRouter

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


@router.get("/capabilities")
def scheduling_capabilities() -> dict[str, object]:
    return {
        "phase": "phase-1-core",
        "modules": [
            "periods",
            "services",
            "workers",
            "assignments",
            "requests",
            "rules",
            "audit",
        ],
    }

