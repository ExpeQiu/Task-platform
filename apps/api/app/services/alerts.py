import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Alert, AlertSeverity, AlertStatus, TaskRun

logger = logging.getLogger(__name__)


async def create_alert(
    db: AsyncSession,
    *,
    alert_type: str,
    content: str,
    severity: str = AlertSeverity.WARNING.value,
    run_id=None,
) -> Alert:
    alert = Alert(
        severity=severity,
        alert_type=alert_type,
        content=content,
        run_id=run_id,
        status=AlertStatus.OPEN.value,
    )
    db.add(alert)
    await db.flush()
    logger.warning("alert created type=%s severity=%s content=%s", alert_type, severity, content)
    return alert


async def scan_timeouts(db: AsyncSession, default_timeout_seconds: int = 300) -> int:
    """Scan running runs for timeout and create alerts."""
    now = datetime.now(UTC)
    count = 0
    from sqlalchemy import select

    from app.models.entities import Task
    from app.services.state_machine import StateMachineService

    result = await db.execute(
        select(TaskRun, Task)
        .join(Task, TaskRun.task_id == Task.id)
        .where(TaskRun.status.in_(["Running", "WaitingFeedback"]))
    )
    sm = StateMachineService(db)
    for run, task in result.all():
        timeout = task.sla_seconds or default_timeout_seconds
        last_updated = run.last_updated_at
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=UTC)
        if now - last_updated > timedelta(seconds=timeout):
            existing = await db.execute(
                select(Alert).where(
                    Alert.run_id == run.id,
                    Alert.alert_type == "AgentTimeout",
                    Alert.status == AlertStatus.OPEN.value,
                )
            )
            if existing.scalar_one_or_none():
                continue
            await create_alert(
                db,
                alert_type="AgentTimeout",
                content=f"Agent 回调超时 (超过 {timeout}s), run={run.id}",
                severity=AlertSeverity.CRITICAL.value,
                run_id=run.id,
            )
            run.task = task
            await sm.transition(run, "Failed", actor="watchdog", detail="Agent timeout")
            run.error_message = "Agent callback timeout"
            count += 1
    return count
