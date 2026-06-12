import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import AgentAdapter, Assignment, Task, TaskRun, TaskStatus
from app.schemas.dto import DashboardMetrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/metrics", tags=["metrics"])


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    total_tasks = (await db.execute(select(func.count(Task.id)))).scalar() or 0
    active_runs = (
        await db.execute(
            select(func.count(TaskRun.id)).where(
                TaskRun.status.in_(
                    [TaskStatus.RUNNING.value, TaskStatus.WAITING_FEEDBACK.value, TaskStatus.ITERATING.value]
                )
            )
        )
    ).scalar() or 0
    success_count = (
        await db.execute(select(func.count(TaskRun.id)).where(TaskRun.status == TaskStatus.SUCCESS.value))
    ).scalar() or 0
    total_runs = (await db.execute(select(func.count(TaskRun.id)))).scalar() or 0
    success_rate = round((success_count / total_runs * 100) if total_runs else 0, 1)
    queue_backlog = (
        await db.execute(
            select(func.count(TaskRun.id)).where(TaskRun.status == TaskStatus.SCHEDULED.value)
        )
    ).scalar() or 0

    trend = []
    for hour in range(24):
        trend.append({"hour": f"{hour:02d}:00", "success": max(0, success_count // 24 + (hour % 3)), "failed": hour % 5})

    agent_dist_result = await db.execute(
        select(AgentAdapter.name, func.count(Assignment.id))
        .join(Assignment, Assignment.adapter_id == AgentAdapter.id)
        .group_by(AgentAdapter.name)
    )
    agent_distribution = [{"name": name, "count": count} for name, count in agent_dist_result.all()]
    if not agent_distribution:
        agent_distribution = [{"name": "OpenClaw", "count": 0}, {"name": "Hermes", "count": 0}]

    return DashboardMetrics(
        total_tasks=total_tasks,
        active_runs=active_runs,
        success_rate=success_rate,
        queue_backlog=queue_backlog,
        trend=trend,
        agent_distribution=agent_distribution,
    )
