import logging
import uuid
from datetime import UTC, datetime, timedelta

from croniter import croniter
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import (
    AgentAdapter,
    Assignment,
    Feedback,
    ScheduledJob,
    Task,
    TaskRun,
    TaskStatus,
)
from app.schemas.dto import TaskCreate, TaskUpdate
from app.services.audit import write_audit
from app.services.loop_guard import LoopGuard
from app.services.state_machine import StateMachineService

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sm = StateMachineService(db)
        self.loop_guard = LoopGuard(db)

    async def create_task(self, payload: TaskCreate, actor: str = "admin") -> Task:
        task = Task(
            name=payload.name,
            objective=payload.objective,
            priority=payload.priority,
            sla_seconds=payload.sla_seconds,
            tags=payload.tags,
            agent_adapter_id=payload.agent_adapter_id,
            schedule_cron=payload.schedule_cron,
            schedule_at=payload.schedule_at,
            loop_config=payload.loop_config.model_dump(),
            retry_config=payload.retry_config.model_dump(),
            status=TaskStatus.DRAFT.value,
        )
        self.db.add(task)
        await self.db.flush()
        await write_audit(
            self.db,
            action="CREATE_TASK",
            target=str(task.id),
            detail=f"创建任务: {task.name}",
            actor=actor,
        )
        logger.info("task created id=%s name=%s", task.id, task.name)
        return task

    async def get_task(self, task_id: uuid.UUID) -> Task:
        result = await self.db.execute(
            select(Task).options(selectinload(Task.runs)).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    async def list_tasks(
        self,
        *,
        status: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Task], int]:
        query = select(Task)
        count_query = select(func.count(Task.id))
        if status:
            query = query.where(Task.status == status)
            count_query = count_query.where(Task.status == status)
        if search:
            query = query.where(Task.name.ilike(f"%{search}%"))
            count_query = count_query.where(Task.name.ilike(f"%{search}%"))
        total = (await self.db.execute(count_query)).scalar() or 0
        result = await self.db.execute(query.order_by(Task.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def update_task(self, task_id: uuid.UUID, payload: TaskUpdate, actor: str = "admin") -> Task:
        task = await self.get_task(task_id)
        if task.status != TaskStatus.DRAFT.value:
            raise HTTPException(status_code=400, detail="Only draft tasks can be updated")
        data = payload.model_dump(exclude_unset=True)
        if "loop_config" in data and data["loop_config"]:
            data["loop_config"] = data["loop_config"].model_dump() if hasattr(data["loop_config"], "model_dump") else data["loop_config"]
        if "retry_config" in data and data["retry_config"]:
            data["retry_config"] = data["retry_config"].model_dump() if hasattr(data["retry_config"], "model_dump") else data["retry_config"]
        for key, value in data.items():
            setattr(task, key, value)
        await write_audit(self.db, action="UPDATE_TASK", target=str(task.id), detail="更新任务", actor=actor)
        return task

    async def submit_task(self, task_id: uuid.UUID, actor: str = "admin") -> TaskRun:
        task = await self.get_task(task_id)
        if task.status != TaskStatus.DRAFT.value:
            raise HTTPException(status_code=400, detail="Task is not in Draft status")
        if not task.agent_adapter_id:
            raise HTTPException(status_code=400, detail="agent_adapter_id is required")

        task.status = TaskStatus.READY.value
        run = TaskRun(task_id=task.id, status=TaskStatus.SCHEDULED.value)
        self.db.add(run)
        await self.db.flush()
        task.status = TaskStatus.READY.value

        if task.schedule_cron or task.schedule_at:
            await self._create_scheduled_job(task)
        else:
            from app.tasks.dispatch import dispatch_task_run

            dispatch_task_run.delay(str(run.id))

        await write_audit(self.db, action="SUBMIT_TASK", target=str(task.id), detail=f"提交任务, run={run.id}", actor=actor)
        return run

    async def _create_scheduled_job(self, task: Task) -> ScheduledJob:
        now = datetime.now(UTC)
        next_run = task.schedule_at
        if task.schedule_cron:
            cron = croniter(task.schedule_cron, now)
            next_run = cron.get_next(datetime)
        idempotency_key = f"{task.id}-{next_run.isoformat() if next_run else 'immediate'}"
        job = ScheduledJob(
            task_id=task.id,
            cron=task.schedule_cron,
            once_at=task.schedule_at,
            next_run_at=next_run,
            idempotency_key=idempotency_key,
        )
        self.db.add(job)
        await self.db.flush()
        logger.info("scheduled job created task=%s next_run=%s", task.id, next_run)
        return job

    async def get_run(self, run_id: uuid.UUID) -> TaskRun:
        result = await self.db.execute(
            select(TaskRun).options(selectinload(TaskRun.task), selectinload(TaskRun.feedbacks)).where(TaskRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            raise HTTPException(status_code=404, detail="TaskRun not found")
        return run

    async def terminate_run(self, run_id: uuid.UUID, actor: str = "admin") -> TaskRun:
        run = await self.get_run(run_id)
        terminal = TaskStatus.TERMINATED.value if run.status == TaskStatus.ITERATING.value else TaskStatus.CANCELLED.value
        await self.sm.transition(run, terminal, actor=actor, detail="Manual terminate")
        await write_audit(self.db, action="TERMINATE_RUN", target=str(run_id), detail="手动终止", actor=actor)
        return run

    async def retry_run(self, run_id: uuid.UUID, actor: str = "admin") -> TaskRun:
        run = await self.get_run(run_id)
        if run.status not in {TaskStatus.FAILED.value, TaskStatus.CANCELLED.value, TaskStatus.TERMINATED.value}:
            raise HTTPException(status_code=400, detail="Run is not in a retriable state")
        task = run.task
        retry_config = task.retry_config or {}
        max_retries = retry_config.get("max_retries", 3)
        if run.retry_count >= max_retries:
            raise HTTPException(status_code=400, detail="Max retries exceeded")

        new_run = TaskRun(
            task_id=task.id,
            status=TaskStatus.SCHEDULED.value,
            retry_count=run.retry_count + 1,
            context=run.context,
        )
        self.db.add(new_run)
        await self.db.flush()
        from app.tasks.dispatch import dispatch_task_run

        dispatch_task_run.delay(str(new_run.id))
        await write_audit(self.db, action="RETRY_RUN", target=str(run_id), detail=f"重试 -> {new_run.id}", actor=actor)
        return new_run

    async def handle_feedback(self, payload, actor: str = "agent") -> TaskRun:
        run = await self.get_run(payload.run_id)
        feedback_id = payload.feedback_id or str(uuid.uuid4())

        existing = await self.db.execute(
            select(Feedback).where(Feedback.run_id == run.id, Feedback.feedback_id == feedback_id)
        )
        if existing.scalar_one_or_none():
            logger.info("duplicate feedback ignored run=%s feedback_id=%s", run.id, feedback_id)
            return run

        feedback = Feedback(
            run_id=run.id,
            feedback_id=feedback_id,
            status=payload.status,
            result_payload=payload.result_payload,
            logs=payload.logs,
            error_code=payload.error_code,
        )
        self.db.add(feedback)

        if run.status == TaskStatus.RUNNING.value:
            await self.sm.transition(run, TaskStatus.WAITING_FEEDBACK.value, actor=actor, detail="Awaiting feedback processing")

        from app.adapters.factory import get_adapter

        adapter = None
        if run.task and run.task.agent_adapter_id:
            adapter_result = await self.db.execute(
                select(AgentAdapter).where(AgentAdapter.id == run.task.agent_adapter_id)
            )
            adapter = adapter_result.scalar_one_or_none()

        status = payload.status.lower()
        if adapter:
            status = get_adapter(adapter).normalize_status(payload.status)
        if status == "success":
            await self.sm.transition(run, TaskStatus.REVIEWING.value, actor=actor, detail="Feedback received")
            await self.sm.transition(run, TaskStatus.SUCCESS.value, actor=actor, detail="Task completed")
        elif status == "failed":
            await self.sm.transition(run, TaskStatus.REVIEWING.value, actor=actor, detail="Feedback failed")
            await self._handle_failure(run, payload.error_code or "AGENT_FAILED")
        elif status == "requires_action":
            run.progress = min(run.progress + 10, 90)
            if run.status != TaskStatus.WAITING_FEEDBACK.value:
                await self.sm.transition(run, TaskStatus.WAITING_FEEDBACK.value, actor=actor, detail="Requires action")
        else:
            run.progress = min(run.progress + 5, 95)

        await write_audit(
            self.db,
            action="AGENT_FEEDBACK",
            target=str(run.id),
            detail=f"status={payload.status}",
            actor=actor,
        )

        if run.workflow_run_id and status == "success":
            await self._advance_workflow(run, payload.result_payload)
        elif run.workflow_run_id and status == "failed":
            await self._fail_workflow(run, payload.error_code or "AGENT_FAILED")

        return run

    async def _advance_workflow(self, run: TaskRun, result_payload: dict) -> None:
        from sqlalchemy.orm import selectinload
        from app.models.entities import WorkflowRun
        from app.services.workflow_engine import WorkflowEngine

        wf_run_result = await self.db.execute(
            select(WorkflowRun)
            .options(selectinload(WorkflowRun.workflow))
            .where(WorkflowRun.id == run.workflow_run_id)
        )
        wf_run = wf_run_result.scalar_one_or_none()
        if not wf_run or not run.workflow_node_id:
            return
        engine = WorkflowEngine(self.db)
        await engine.on_agent_node_complete(wf_run, run.workflow_node_id, result_payload or {})
        logger.info("workflow advanced after feedback run=%s wf_run=%s node=%s", run.id, wf_run.id, run.workflow_node_id)

    async def _fail_workflow(self, run: TaskRun, error: str) -> None:
        from app.models.entities import WorkflowRun, WorkflowRunStatus

        wf_run_result = await self.db.execute(select(WorkflowRun).where(WorkflowRun.id == run.workflow_run_id))
        wf_run = wf_run_result.scalar_one_or_none()
        if not wf_run:
            return
        wf_run.status = WorkflowRunStatus.FAILED.value
        wf_run.error_message = error
        from datetime import UTC, datetime

        wf_run.finished_at = datetime.now(UTC)
        logger.error("workflow failed from agent feedback wf_run=%s error=%s", wf_run.id, error)

    async def _handle_failure(self, run: TaskRun, error_code: str) -> None:
        from app.services.alerts import create_alert
        from app.models.entities import AlertSeverity

        run.error_message = error_code
        task = run.task
        retry_config = task.retry_config or {}
        max_retries = retry_config.get("max_retries", 3)

        await create_alert(
            self.db,
            alert_type="TaskFailed",
            content=f"任务失败: {error_code}, run={run.id}",
            severity=AlertSeverity.WARNING.value,
            run_id=run.id,
        )
        await self.sm.transition(run, TaskStatus.FAILED.value, actor="system", detail=error_code)

        if run.retry_count < max_retries:
            backoff = retry_config.get("backoff_base_seconds", 30) * (2 ** run.retry_count)
            from app.tasks.dispatch import dispatch_task_run

            new_run = TaskRun(
                task_id=task.id,
                status=TaskStatus.SCHEDULED.value,
                retry_count=run.retry_count + 1,
                context=run.context,
            )
            self.db.add(new_run)
            await self.db.flush()
            dispatch_task_run.apply_async(args=[str(new_run.id)], countdown=backoff)
            logger.info("auto retry scheduled run=%s countdown=%s", new_run.id, backoff)

    async def dispatch_run(self, run_id: uuid.UUID) -> Assignment:
        run = await self.get_run(run_id)
        task = run.task

        if not await self.loop_guard.enforce_or_fail(run, task.loop_config or {}):
            await self.sm.transition(run, TaskStatus.FAILED.value, actor="loop_guard", detail="Loop limit exceeded")
            return None  # type: ignore

        run.iteration_count += 1
        adapter_result = await self.db.execute(select(AgentAdapter).where(AgentAdapter.id == task.agent_adapter_id))
        adapter = adapter_result.scalar_one_or_none()
        if not adapter:
            raise HTTPException(status_code=400, detail="Adapter not found")
        if not adapter.is_online:
            await self.sm.transition(
                run,
                TaskStatus.FAILED.value,
                actor="scheduler",
                detail=f"Adapter '{adapter.name}' is offline",
            )
            logger.warning("dispatch blocked adapter offline run=%s adapter=%s", run.id, adapter.name)
            return None  # type: ignore

        if run.status == TaskStatus.SCHEDULED.value:
            await self.sm.transition(run, TaskStatus.RUNNING.value, actor="scheduler", detail="Dispatch started")
        elif run.status in {TaskStatus.ITERATING.value, TaskStatus.WAITING_FEEDBACK.value}:
            await self.sm.transition(run, TaskStatus.RUNNING.value, actor="scheduler", detail="Next iteration")

        from app.adapters.factory import get_adapter

        adapter_impl = get_adapter(adapter)
        assignment = await adapter_impl.dispatch(self.db, run, task, adapter)
        run.progress = min(run.progress + 15, 85)
        await self.sm.transition(run, TaskStatus.WAITING_FEEDBACK.value, actor="scheduler", detail="Waiting agent callback")
        return assignment

    async def get_run_logs(self, run_id: uuid.UUID) -> list[dict]:
        run = await self.get_run(run_id)
        logs: list[dict] = []
        for fb in run.feedbacks:
            logs.append(
                {
                    "timestamp": fb.received_at,
                    "source": "agent",
                    "message": f"Feedback: {fb.status}",
                    "metadata": {"logs": fb.logs, "result": fb.result_payload},
                }
            )
        from app.models.entities import AuditEvent

        audit_result = await self.db.execute(
            select(AuditEvent).where(AuditEvent.target == str(run_id)).order_by(AuditEvent.created_at)
        )
        for event in audit_result.scalars().all():
            logs.append(
                {
                    "timestamp": event.created_at,
                    "source": "audit",
                    "message": f"{event.action}: {event.detail}",
                    "metadata": event.metadata_json,
                }
            )
        logs.sort(key=lambda x: x["timestamp"])
        return logs
