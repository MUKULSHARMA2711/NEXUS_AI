from fastapi import APIRouter

from nexus.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health Check")
def get_health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "nexus",
        "version": settings.app_version,
        "environment": settings.environment,
    }
