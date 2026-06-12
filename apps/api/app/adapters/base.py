import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.entities import AgentAdapter, Assignment, Task, TaskRun

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseAgentAdapter(ABC):
    def __init__(self, adapter: AgentAdapter):
        self.adapter = adapter

    def build_payload(self, run: TaskRun, task: Task) -> dict:
        return {
            "task_id": str(task.id),
            "run_id": str(run.id),
            "objective": task.objective,
            "context": run.context,
            "constraints": {"timeout": task.sla_seconds, "max_tokens": 8000},
            "callback_url": f"{settings.api_base_url}/v1/webhooks/agent_feedback",
        }

    @abstractmethod
    async def dispatch(
        self, db: AsyncSession, run: TaskRun, task: Task, adapter: AgentAdapter
    ) -> Assignment:
        pass

    async def health_check(self) -> dict:
        return {"status": "ok", "adapter": self.adapter.name}


class PushAdapter(BaseAgentAdapter):
    async def dispatch(
        self, db: AsyncSession, run: TaskRun, task: Task, adapter: AgentAdapter
    ) -> Assignment:
        payload = self.build_payload(run, task)
        assignment = Assignment(
            run_id=run.id,
            adapter_id=adapter.id,
            dispatched_at=datetime.now(UTC),
            callback_deadline=datetime.now(UTC) + timedelta(seconds=task.sla_seconds),
            payload=payload,
        )
        db.add(assignment)
        await db.flush()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{adapter.endpoint}/v1/tasks", json=payload)
                resp.raise_for_status()
            logger.info("push dispatch ok run=%s adapter=%s", run.id, adapter.name)
        except Exception as exc:
            logger.error("push dispatch failed run=%s error=%s", run.id, exc)
            raise

        return assignment


class PullAdapter(BaseAgentAdapter):
    PULL_QUEUE_KEY = "agent:pull:queue"

    async def dispatch(
        self, db: AsyncSession, run: TaskRun, task: Task, adapter: AgentAdapter
    ) -> Assignment:
        import json

        import redis.asyncio as aioredis

        payload = self.build_payload(run, task)
        assignment = Assignment(
            run_id=run.id,
            adapter_id=adapter.id,
            dispatched_at=datetime.now(UTC),
            callback_deadline=datetime.now(UTC) + timedelta(seconds=task.sla_seconds),
            payload=payload,
        )
        db.add(assignment)
        await db.flush()

        queue_item = {
            "assignment_id": str(assignment.id),
            "adapter_name": adapter.name,
            **payload,
        }
        r = aioredis.from_url(settings.redis_url)
        await r.rpush(f"{self.PULL_QUEUE_KEY}:{adapter.name}", json.dumps(queue_item))
        await r.aclose()
        logger.info("pull task queued run=%s adapter=%s", run.id, adapter.name)
        return assignment

    @classmethod
    async def pull_next(cls, adapter_name: str) -> dict | None:
        import json

        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        item = await r.lpop(f"{cls.PULL_QUEUE_KEY}:{adapter_name}")
        await r.aclose()
        if item:
            return json.loads(item)
        return None
