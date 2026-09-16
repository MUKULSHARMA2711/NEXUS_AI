from fastapi import FastAPI

from nexus.api.v1.router import api_router
from nexus.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "description": settings.app_description,
        "status": "operational",
    }
