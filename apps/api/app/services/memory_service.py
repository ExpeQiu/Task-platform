"""长期记忆服务 — 跨任务经验沉淀与上下文注入。"""

import logging
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import MemoryEntry, MemoryScope, Task

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_entry(
        self,
        *,
        scope: str,
        key: str,
        content: str,
        scope_ref: str | None = None,
        metadata: dict | None = None,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            scope=scope,
            scope_ref=scope_ref,
            key=key,
            content=content,
            metadata_json=metadata or {},
        )
        self.db.add(entry)
        await self.db.flush()
        logger.info("memory saved scope=%s key=%s id=%s", scope, key, entry.id)
        return entry

    async def list_entries(
        self,
        *,
        scope: str | None = None,
        scope_ref: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        query = select(MemoryEntry).order_by(MemoryEntry.updated_at.desc()).limit(limit)
        if scope:
            query = query.where(MemoryEntry.scope == scope)
        if scope_ref:
            query = query.where(MemoryEntry.scope_ref == scope_ref)
        if search:
            query = query.where(
                or_(MemoryEntry.key.ilike(f"%{search}%"), MemoryEntry.content.ilike(f"%{search}%"))
            )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_relevant_for_task(self, task: Task, *, limit: int = 10) -> list[MemoryEntry]:
        """按 global → task_type(tag) → task_id 优先级召回记忆。"""
        collected: list[MemoryEntry] = []
        seen: set[uuid.UUID] = set()

        async def _fetch(scope: str, scope_ref: str | None) -> None:
            q = (
                select(MemoryEntry)
                .where(MemoryEntry.scope == scope)
                .order_by(MemoryEntry.updated_at.desc())
                .limit(limit)
            )
            if scope_ref:
                q = q.where(MemoryEntry.scope_ref == scope_ref)
            result = await self.db.execute(q)
            for entry in result.scalars().all():
                if entry.id not in seen:
                    seen.add(entry.id)
                    collected.append(entry)

        await _fetch(MemoryScope.GLOBAL.value, None)
        for tag in task.tags or []:
            await _fetch(MemoryScope.TASK_TYPE.value, str(tag))
        await _fetch(MemoryScope.TASK.value, str(task.id))
        return collected[:limit]

    async def build_context_snippet(self, task: Task) -> dict:
        entries = await self.get_relevant_for_task(task)
        if not entries:
            return {}
        return {
            "long_term_memory": [
                {"key": e.key, "content": e.content, "scope": e.scope, "metadata": e.metadata_json}
                for e in entries
            ]
        }

    async def record_run_outcome(self, task: Task, run_id: uuid.UUID, *, success: bool, summary: str) -> None:
        """任务结束后沉淀简要经验。"""
        key = f"task:{task.id}:{'success' if success else 'failed'}"
        await self.save_entry(
            scope=MemoryScope.TASK.value,
            scope_ref=str(task.id),
            key=key,
            content=summary[:2000],
            metadata={"run_id": str(run_id), "task_name": task.name, "success": success},
        )
