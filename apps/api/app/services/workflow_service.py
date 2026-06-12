import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import WorkflowDefinition, WorkflowRun, WorkflowRunStatus, WorkflowStatus
from app.schemas.dto import WorkflowCreate, WorkflowDag, WorkflowUpdate
from app.services.audit import write_audit
from app.services.dag_validator import validate_dag

logger = logging.getLogger(__name__)

DEFAULT_DAG = {
    "nodes": [
        {"id": "start", "type": "start", "label": "接收 Webhook", "config": {"trigger": "webhook"}, "position": {"x": 250, "y": 40}},
        {"id": "openclaw", "type": "agent", "label": "OpenClaw 抓取", "config": {"objective": "抓取竞品数据"}, "position": {"x": 120, "y": 180}},
        {"id": "hermes", "type": "agent", "label": "Hermes 总结", "config": {"objective": "生成分析报告"}, "position": {"x": 380, "y": 180}},
        {"id": "end", "type": "end", "label": "输出报告并告警", "config": {"action": "notify"}, "position": {"x": 250, "y": 320}},
    ],
    "edges": [
        {"id": "e1", "source": "start", "target": "openclaw"},
        {"id": "e2", "source": "start", "target": "hermes"},
        {"id": "e3", "source": "openclaw", "target": "end"},
        {"id": "e4", "source": "hermes", "target": "end"},
    ],
}


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_workflow(self, payload: WorkflowCreate, actor: str = "admin") -> WorkflowDefinition:
        dag = payload.dag.model_dump() if payload.dag.nodes else DEFAULT_DAG
        wf = WorkflowDefinition(
            name=payload.name,
            description=payload.description,
            dag=dag,
            status=WorkflowStatus.DRAFT.value,
        )
        self.db.add(wf)
        await self.db.flush()
        await write_audit(self.db, action="CREATE_WORKFLOW", target=str(wf.id), detail=f"创建流程: {wf.name}", actor=actor)
        logger.info("workflow created id=%s name=%s", wf.id, wf.name)
        return wf

    async def get_workflow(self, workflow_id: uuid.UUID) -> WorkflowDefinition:
        result = await self.db.execute(select(WorkflowDefinition).where(WorkflowDefinition.id == workflow_id))
        wf = result.scalar_one_or_none()
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return wf

    async def list_workflows(
        self,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[WorkflowDefinition], int]:
        query = select(WorkflowDefinition)
        count_query = select(func.count(WorkflowDefinition.id))
        if status:
            query = query.where(WorkflowDefinition.status == status)
            count_query = count_query.where(WorkflowDefinition.status == status)
        total = (await self.db.execute(count_query)).scalar() or 0
        result = await self.db.execute(
            query.order_by(WorkflowDefinition.updated_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all()), total

    async def update_workflow(
        self, workflow_id: uuid.UUID, payload: WorkflowUpdate, actor: str = "admin"
    ) -> WorkflowDefinition:
        wf = await self.get_workflow(workflow_id)
        if wf.status != WorkflowStatus.DRAFT.value:
            raise HTTPException(status_code=400, detail="Only draft workflows can be updated")
        data = payload.model_dump(exclude_unset=True)
        if "dag" in data and data["dag"]:
            data["dag"] = data["dag"].model_dump() if hasattr(data["dag"], "model_dump") else data["dag"]
        for key, value in data.items():
            setattr(wf, key, value)
        await write_audit(self.db, action="UPDATE_WORKFLOW", target=str(wf.id), detail="更新流程草稿", actor=actor)
        logger.info("workflow updated id=%s", wf.id)
        return wf

    async def validate_workflow(self, workflow_id: uuid.UUID) -> tuple[bool, list[str], list[str]]:
        wf = await self.get_workflow(workflow_id)
        dag = WorkflowDag.model_validate(wf.dag)
        return validate_dag(dag)

    async def publish_workflow(self, workflow_id: uuid.UUID, actor: str = "admin") -> WorkflowDefinition:
        wf = await self.get_workflow(workflow_id)
        if wf.status != WorkflowStatus.DRAFT.value:
            raise HTTPException(status_code=400, detail="Only draft workflows can be published")

        dag = WorkflowDag.model_validate(wf.dag)
        valid, errors, _warnings = validate_dag(dag)
        if not valid:
            raise HTTPException(status_code=400, detail={"message": "DAG validation failed", "errors": errors})

        wf.status = WorkflowStatus.PUBLISHED.value
        wf.version += 1
        await write_audit(
            self.db,
            action="PUBLISH_WORKFLOW",
            target=str(wf.id),
            detail=f"发布流程 v{wf.version}",
            actor=actor,
        )
        logger.info("workflow published id=%s version=%s", wf.id, wf.version)
        return wf

    async def get_run(self, run_id: uuid.UUID) -> WorkflowRun:
        result = await self.db.execute(
            select(WorkflowRun)
            .options(selectinload(WorkflowRun.workflow))
            .where(WorkflowRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            raise HTTPException(status_code=404, detail="WorkflowRun not found")
        return run

    async def list_runs(self, workflow_id: uuid.UUID, limit: int = 20) -> list[WorkflowRun]:
        result = await self.db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.workflow_id == workflow_id)
            .order_by(WorkflowRun.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
