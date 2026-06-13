import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.dto import (
    AgentFeedbackWebhook,
    RunLogEntry,
    RunLogsResponse,
    TaskCreate,
    TaskDetailResponse,
    TaskListItemResponse,
    TaskListResponse,
    TaskResponse,
    TaskRunResponse,
    TaskUpdate,
)
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    return await service.create_task(payload)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: str | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    items, total = await service.list_tasks(status=status, search=search, skip=skip, limit=limit)
    enriched: list[TaskListItemResponse] = []
    for task in items:
        latest_run = None
        if task.runs:
            latest = sorted(task.runs, key=lambda r: r.created_at, reverse=True)[0]
            latest_run = TaskRunResponse.model_validate(latest)
        item = TaskListItemResponse.model_validate(task)
        item.latest_run = latest_run
        enriched.append(item)
    return TaskListResponse(items=enriched, total=total)


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    task = await service.get_task(task_id)
    latest_run = None
    if task.runs:
        latest = sorted(task.runs, key=lambda r: r.created_at, reverse=True)[0]
        latest_run = TaskRunResponse.model_validate(latest)
    resp = TaskDetailResponse.model_validate(task)
    resp.latest_run = latest_run
    return resp


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: UUID, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    return await service.update_task(task_id, payload)


@router.post("/{task_id}/submit", response_model=TaskRunResponse)
async def submit_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    run = await service.submit_task(task_id)
    return run
