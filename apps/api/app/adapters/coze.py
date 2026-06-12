import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import PushAdapter
from app.models.entities import AgentAdapter, Assignment, Task, TaskRun

logger = logging.getLogger(__name__)

DEFAULT_STATUS_MAPPING = {
    "success": "success",
    "completed": "success",
    "failed": "failed",
    "error": "failed",
    "in_progress": "requires_action",
    "requires_action": "requires_action",
}


class CozeAdapter(PushAdapter):
    """Coze / 扣子 Bot 适配器。"""

    def build_payload(self, run: TaskRun, task: Task) -> dict:
        base = super().build_payload(run, task)
        auth = self.adapter.auth_config or {}
        return {
            **base,
            "coze": {
                "bot_id": auth.get("bot_id", ""),
                "user_id": str(run.id),
                "conversation_id": run.context.get("conversation_id"),
            },
            "input": task.objective,
        }

    def normalize_status(self, raw_status: str) -> str:
        if self.adapter.status_mapping:
            return super().normalize_status(raw_status)
        return DEFAULT_STATUS_MAPPING.get(raw_status.lower(), raw_status.lower())

    def _dispatch_path(self) -> str:
        return (self.adapter.auth_config or {}).get("dispatch_path", "/v1/tasks")

    async def dispatch(
        self, db: AsyncSession, run: TaskRun, task: Task, adapter: AgentAdapter
    ) -> Assignment:
        logger.info("coze dispatch run=%s bot_id=%s", run.id, (adapter.auth_config or {}).get("bot_id"))
        return await self._post_dispatch(db, run, task, adapter, self._dispatch_path())
