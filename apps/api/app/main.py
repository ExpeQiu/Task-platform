import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import setup_logging
from app.database import engine
from app.models.entities import Base
from app.routers import adapters, alerts, audit, mcp, memory, metrics, runs, skills, tasks, workflows

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Task Platform API starting")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")
    yield
    logger.info("Task Platform API shutting down")


app = FastAPI(title="Task Platform API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(runs.router)
app.include_router(alerts.router)
app.include_router(audit.router)
app.include_router(adapters.router)
app.include_router(mcp.router)
app.include_router(skills.router)
app.include_router(memory.router)
app.include_router(metrics.router)
app.include_router(workflows.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "task-platform-api"}
