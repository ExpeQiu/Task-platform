import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import PushAdapter
from app.adapters.coze import DEFAULT_STATUS_MAPPING
from app.models.entities import AgentAdapter, Assignment, Task, TaskRun

logger = logging.getLogger(__name__)


class DifyAdapter(PushAdapter):
    """Dify Workflow 适配器。"""

    def build_payload(self, run: TaskRun, task: Task) -> dict:
        base = super().build_payload(run, task)
        auth = self.adapter.auth_config or {}
        return {
            **base,
            "inputs": {
                "objective": task.objective,
                **(run.context or {}),
            },
            "response_mode": auth.get("response_mode", "blocking"),
            "user": str(run.id),
        }

    def normalize_status(self, raw_status: str) -> str:
        if self.adapter.status_mapping:
            return super().normalize_status(raw_status)
        mapping = {**DEFAULT_STATUS_MAPPING, "succeeded": "success", "stopped": "failed"}
        return mapping.get(raw_status.lower(), raw_status.lower())

    def _dispatch_path(self) -> str:
        return (self.adapter.auth_config or {}).get("dispatch_path", "/v1/workflows/run")

    async def dispatch(
        self, db: AsyncSession, run: TaskRun, task: Task, adapter: AgentAdapter
    ) -> Assignment:
        path = self._dispatch_path()
        if adapter.endpoint.rstrip("/").endswith("8100") and path == "/v1/workflows/run":
            path = "/v1/tasks"
        logger.info("dify dispatch run=%s path=%s", run.id, path)
        return await self._post_dispatch(db, run, task, adapter, path)
