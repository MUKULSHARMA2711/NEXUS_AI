from fastapi import FastAPI

app = FastAPI(
    title="NEXUS",
    description="AI Engineering Intelligence Platform",
    version="0.1.0",
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "name": "NEXUS",
        "description": "AI Engineering Intelligence Platform",
        "status": "operational",
    }
