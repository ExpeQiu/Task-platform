import asyncio
import logging
import uuid
from datetime import UTC, datetime

from croniter import croniter
from sqlalchemy import select

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.entities import ScheduledJob, Task, TaskRun, TaskStatus
from app.services.audit import write_audit
from app.services.state_machine import StateMachineService
from app.tasks.dispatch import dispatch_task_run

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.scheduler.process_scheduled_jobs")
def process_scheduled_jobs():
    async def _process():
        async with AsyncSessionLocal() as db:
            now = datetime.now(UTC)
            result = await db.execute(
                select(ScheduledJob).where(ScheduledJob.is_active == True, ScheduledJob.next_run_at <= now)  # noqa: E712
            )
            jobs = result.scalars().all()
            sm = StateMachineService(db)
            for job in jobs:
                task_result = await db.execute(select(Task).where(Task.id == job.task_id))
                task = task_result.scalar_one_or_none()
                if not task:
                    continue
                run = TaskRun(task_id=task.id, status=TaskStatus.SCHEDULED.value)
                db.add(run)
                await db.flush()
                dispatch_task_run.delay(str(run.id))
                job.last_run_at = now
                if job.cron:
                    cron = croniter(job.cron, now)
                    job.next_run_at = cron.get_next(datetime)
                    job.idempotency_key = f"{task.id}-{job.next_run_at.isoformat()}"
                else:
                    job.is_active = False
                await write_audit(
                    db,
                    action="SCHEDULED_TRIGGER",
                    target=str(task.id),
                    detail=f"run={run.id}",
                )
                logger.info("scheduled job triggered task=%s run=%s", task.id, run.id)
            await db.commit()
            return len(jobs)

    return _run_async(_process())
