import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.dto import (
    AiOrchestratorRequest,
    AiOrchestratorResponse,
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowRunResponse,
    WorkflowRunTrigger,
    WorkflowUpdate,
    WorkflowValidateResult,
)
from app.services.ai_orchestrator import bind_adapters_to_dag, chat_orchestrate
from app.services.workflow_engine import WorkflowEngine
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


@router.post("/ai/chat", response_model=AiOrchestratorResponse)
async def ai_orchestrator_chat(payload: AiOrchestratorRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.entities import AgentAdapter

    result = await db.execute(select(AgentAdapter.name))
    adapter_names = [row[0] for row in result.all()]
    history = [{"role": m.role, "content": m.content} for m in payload.history]
    response = await chat_orchestrate(payload.message, history, adapter_names)

    if response.dag:
        adapter_rows = await db.execute(select(AgentAdapter))
        adapters = [{"id": a.id, "name": a.name} for a in adapter_rows.scalars().all()]
        response.dag = bind_adapters_to_dag(response.dag, adapters)

    logger.info("ai chat completed has_dag=%s", response.dag is not None)
    return response


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(payload: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    service = WorkflowService(db)
    return await service.create_workflow(payload)


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    status: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    items, total = await service.list_workflows(status=status, skip=skip, limit=limit)
    return WorkflowListResponse(items=items, total=total)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID, db: AsyncSession = Depends(get_db)):
    service = WorkflowService(db)
    return await service.get_workflow(workflow_id)


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: UUID, payload: WorkflowUpdate, db: AsyncSession = Depends(get_db)):
    service = WorkflowService(db)
    return await service.update_workflow(workflow_id, payload)


@router.post("/{workflow_id}/validate", response_model=WorkflowValidateResult)
async def validate_workflow(workflow_id: UUID, db: AsyncSession = Depends(get_db)):
    service = WorkflowService(db)
    valid, errors, warnings = await service.validate_workflow(workflow_id)
    return WorkflowValidateResult(valid=valid, errors=errors, warnings=warnings)


@router.post("/{workflow_id}/publish", response_model=WorkflowResponse)
async def publish_workflow(workflow_id: UUID, db: AsyncSession = Depends(get_db)):
    service = WorkflowService(db)
    return await service.publish_workflow(workflow_id)


@router.post("/{workflow_id}/trigger", response_model=WorkflowRunResponse)
async def trigger_workflow(
    workflow_id: UUID,
    payload: WorkflowRunTrigger | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = WorkflowService(db)
    wf = await service.get_workflow(workflow_id)
    engine = WorkflowEngine(db)
    ctx = payload.context if payload else {}
    run = await engine.trigger_run(wf, context=ctx)
    logger.info("workflow triggered workflow_id=%s run_id=%s", workflow_id, run.id)
    return run


@router.get("/{workflow_id}/runs", response_model=list[WorkflowRunResponse])
async def list_workflow_runs(workflow_id: UUID, db: AsyncSession = Depends(get_db)):
    service = WorkflowService(db)
    await service.get_workflow(workflow_id)
    return await service.list_runs(workflow_id)


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    service = WorkflowService(db)
    return await service.get_run(run_id)
