import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import AgentAdapter, Assignment, TaskRun, TaskStatus

logger = logging.getLogger(__name__)


async def get_adapter_stats(db: AsyncSession) -> list[dict]:
    adapters = (await db.execute(select(AgentAdapter).order_by(AgentAdapter.name))).scalars().all()
    stats: list[dict] = []

    for adapter in adapters:
        result = await db.execute(
            select(Assignment)
            .options(
                selectinload(Assignment.run).selectinload(TaskRun.feedbacks),
            )
            .where(Assignment.adapter_id == adapter.id)
        )
        assignments = result.scalars().all()
        total = len(assignments)
        success_count = 0
        failed_count = 0
        latencies: list[float] = []

        for assignment in assignments:
            run = assignment.run
            if not run:
                continue
            if run.status == TaskStatus.SUCCESS.value:
                success_count += 1
            elif run.status == TaskStatus.FAILED.value:
                failed_count += 1

            if assignment.dispatched_at and run.feedbacks:
                first_fb = min(run.feedbacks, key=lambda f: f.received_at)
                delta = (first_fb.received_at - assignment.dispatched_at).total_seconds() * 1000
                if delta >= 0:
                    latencies.append(delta)

        terminal = success_count + failed_count
        success_rate = round((success_count / terminal * 100) if terminal else 0, 1)
        avg_latency_ms = round(sum(latencies) / len(latencies), 1) if latencies else None

        stats.append(
            {
                "adapter_id": str(adapter.id),
                "name": adapter.name,
                "adapter_type": adapter.adapter_type,
                "protocol": adapter.protocol,
                "is_online": adapter.is_online,
                "total_assignments": total,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": success_rate,
                "avg_latency_ms": avg_latency_ms,
            }
        )

    logger.debug("adapter stats computed count=%s", len(stats))
    return stats
