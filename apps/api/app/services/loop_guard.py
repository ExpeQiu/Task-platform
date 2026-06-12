import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AlertSeverity, TaskRun
from app.services.alerts import create_alert

logger = logging.getLogger(__name__)


class LoopGuard:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_before_iteration(self, run: TaskRun, loop_config: dict) -> tuple[bool, str | None]:
        max_iterations = loop_config.get("max_iterations", 10)
        max_duration = loop_config.get("max_duration_seconds", 3600)

        if run.iteration_count >= max_iterations:
            msg = f"超过最大循环次数 {max_iterations}"
            logger.warning("loop guard triggered run=%s reason=%s", run.id, msg)
            return False, msg

        if run.started_at:
            started = run.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            elapsed = (datetime.now(UTC) - started).total_seconds()
            if elapsed >= max_duration:
                msg = f"超过最大执行时长 {max_duration}s"
                logger.warning("loop guard triggered run=%s reason=%s", run.id, msg)
                return False, msg

        return True, None

    async def enforce_or_fail(self, run: TaskRun, loop_config: dict) -> bool:
        ok, reason = await self.check_before_iteration(run, loop_config)
        if ok:
            return True
        await create_alert(
            self.db,
            alert_type="LoopLimitExceeded",
            content=f"{reason}, run={run.id}",
            severity=AlertSeverity.CRITICAL.value,
            run_id=run.id,
        )
        run.error_message = reason
        return False
