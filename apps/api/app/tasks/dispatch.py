import asyncio
import logging

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.dispatch.dispatch_task_run")
def dispatch_task_run(run_id: str):
    async def _dispatch():
        async with AsyncSessionLocal() as db:
            service = TaskService(db)
            try:
                await service.dispatch_run(__import__("uuid").UUID(run_id))
                await db.commit()
                logger.info("dispatch completed run_id=%s", run_id)
            except Exception as exc:
                await db.rollback()
                logger.exception("dispatch failed run_id=%s error=%s", run_id, exc)
                raise

    return _run_async(_dispatch())
