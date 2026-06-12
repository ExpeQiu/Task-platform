import asyncio
import logging

from app.celery_app import celery_app
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.alerts import scan_timeouts

logger = logging.getLogger(__name__)
settings = get_settings()


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.watchdog.run_watchdog")
def run_watchdog():
    async def _scan():
        async with AsyncSessionLocal() as db:
            count = await scan_timeouts(db, settings.default_timeout_seconds)
            await db.commit()
            logger.info("watchdog scan complete alerts=%s", count)
            return count

    return _run_async(_scan())
