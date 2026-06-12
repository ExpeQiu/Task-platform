import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import PullAdapter
from app.database import get_db
from app.schemas.dto import AgentFeedbackWebhook, PullTaskResponse, RunLogEntry, RunLogsResponse, TaskRunResponse
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["runs"])


@router.get("/v1/runs/{run_id}", response_model=TaskRunResponse)
async def get_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    return await service.get_run(run_id)


@router.post("/v1/runs/{run_id}/retry", response_model=TaskRunResponse)
async def retry_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    return await service.retry_run(run_id)


@router.post("/v1/runs/{run_id}/terminate", response_model=TaskRunResponse)
async def terminate_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    return await service.terminate_run(run_id)


@router.get("/v1/runs/{run_id}/logs", response_model=RunLogsResponse)
async def get_run_logs(run_id: UUID, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    logs = await service.get_run_logs(run_id)
    return RunLogsResponse(
        run_id=run_id,
        logs=[RunLogEntry(**entry) for entry in logs],
    )


@router.post("/v1/webhooks/agent_feedback")
async def agent_feedback(payload: AgentFeedbackWebhook, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    run = await service.handle_feedback(payload)
    logger.info("webhook feedback processed run=%s status=%s", run.id, payload.status)
    return {"ok": True, "run_id": str(run.id), "status": run.status}


@router.get("/v1/agent/pull", response_model=PullTaskResponse | None)
async def pull_task(adapter_name: str = Query(...), db: AsyncSession = Depends(get_db)):
    item = await PullAdapter.pull_next(adapter_name)
    if not item:
        return None
    return PullTaskResponse(
        assignment_id=UUID(item["assignment_id"]),
        run_id=UUID(item["run_id"]),
        task_id=item["task_id"],
        objective=item["objective"],
        context=item.get("context", {}),
        constraints=item.get("constraints", {}),
        callback_url=item["callback_url"],
    )
