from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health Check")
def get_health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "nexus",
        "version": "0.1.0",
    }
