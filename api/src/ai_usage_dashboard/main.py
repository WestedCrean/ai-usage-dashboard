from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_usage_dashboard.config import settings
from ai_usage_dashboard.database import init_db
from ai_usage_dashboard.routers import models_router, projects, usage


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Usage Dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(usage.router, prefix=settings.api_v1_prefix)
app.include_router(models_router.router, prefix=settings.api_v1_prefix)
app.include_router(projects.router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


def main():
    import uvicorn

    uvicorn.run("ai_usage_dashboard.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
