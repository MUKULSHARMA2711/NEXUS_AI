from fastapi import FastAPI

from nexus.api.v1.router import api_router

app = FastAPI(
    title="NEXUS",
    description="AI Engineering Intelligence Platform",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "name": "NEXUS",
        "description": "AI Engineering Intelligence Platform",
        "status": "operational",
    }
