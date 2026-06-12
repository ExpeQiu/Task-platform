import logging
import time
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
            "callback_auth": self._callback_auth_meta(),
        }

    def _callback_auth_meta(self) -> dict:
        from app.services.webhook_auth import callback_auth_meta

        return callback_auth_meta()

    def build_auth_headers(self) -> dict[str, str]:
        auth = self.adapter.auth_config or {}
        headers: dict[str, str] = {}
        bearer = auth.get("bearer_token")
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
            return headers
        api_key = auth.get("api_key")
        header_name = auth.get("api_key_header", "X-API-Key")
        if api_key:
            headers[header_name] = api_key
        return headers

    def normalize_status(self, raw_status: str) -> str:
        mapping = self.adapter.status_mapping or {}
        mapped = mapping.get(raw_status, raw_status)
        return str(mapped).lower()

    @abstractmethod
    async def dispatch(
        self, db: AsyncSession, run: TaskRun, task: Task, adapter: AgentAdapter
    ) -> Assignment:
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        pass


class PushAdapter(BaseAgentAdapter):
    async def _post_dispatch(
        self,
        db: AsyncSession,
        run: TaskRun,
        task: Task,
        adapter: AgentAdapter,
        path: str = "/v1/tasks",
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

        headers = self.build_auth_headers()
        url = f"{adapter.endpoint.rstrip('/')}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
            logger.info("push dispatch ok run=%s adapter=%s url=%s", run.id, adapter.name, url)
        except Exception as exc:
            logger.error("push dispatch failed run=%s adapter=%s url=%s error=%s", run.id, adapter.name, url, exc)
            raise

        return assignment

    async def dispatch(
        self, db: AsyncSession, run: TaskRun, task: Task, adapter: AgentAdapter
    ) -> Assignment:
        return await self._post_dispatch(db, run, task, adapter, "/v1/tasks")

    async def health_check(self) -> dict:
        url = f"{self.adapter.endpoint.rstrip('/')}/health"
        headers = self.build_auth_headers()
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
            latency_ms = round((time.monotonic() - started) * 1000)
            logger.info("push health ok adapter=%s latency_ms=%s", self.adapter.name, latency_ms)
            return {
                "status": "ok",
                "adapter": self.adapter.name,
                "protocol": "push",
                "latency_ms": latency_ms,
                "endpoint_checked": url,
            }
        except Exception as exc:
            logger.warning("push health failed adapter=%s error=%s", self.adapter.name, exc)
            return {
                "status": "error",
                "adapter": self.adapter.name,
                "protocol": "push",
                "endpoint_checked": url,
                "error": str(exc),
            }


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
        queue_key = f"{self.PULL_QUEUE_KEY}:{adapter.name}"
        await r.rpush(queue_key, json.dumps(queue_item))
        queue_depth = await r.llen(queue_key)
        await r.aclose()
        logger.info(
            "pull task queued run=%s adapter=%s queue_depth=%s",
            run.id,
            adapter.name,
            queue_depth,
        )
        return assignment

    async def health_check(self) -> dict:
        import redis.asyncio as aioredis

        queue_key = f"{self.PULL_QUEUE_KEY}:{self.adapter.name}"
        pull_url = f"{settings.api_base_url}/v1/agent/pull?adapter_name={self.adapter.name}"
        try:
            r = aioredis.from_url(settings.redis_url)
            queue_depth = await r.llen(queue_key)
            await r.ping()
            await r.aclose()
            logger.info(
                "pull health ok adapter=%s queue_depth=%s",
                self.adapter.name,
                queue_depth,
            )
            return {
                "status": "ok",
                "adapter": self.adapter.name,
                "protocol": "pull",
                "queue_depth": queue_depth,
                "pull_url": pull_url,
            }
        except Exception as exc:
            logger.warning("pull health failed adapter=%s error=%s", self.adapter.name, exc)
            return {
                "status": "error",
                "adapter": self.adapter.name,
                "protocol": "pull",
                "pull_url": pull_url,
                "error": str(exc),
            }

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
