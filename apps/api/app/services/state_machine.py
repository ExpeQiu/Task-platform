import logging
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import TaskRun, TaskStatus
from app.services.audit import write_audit

logger = logging.getLogger(__name__)

# Valid transitions: from_status -> set of to_status
TRANSITIONS: dict[str, set[str]] = {
    TaskStatus.DRAFT.value: {TaskStatus.READY.value},
    TaskStatus.READY.value: {TaskStatus.SCHEDULED.value, TaskStatus.CANCELLED.value},
    TaskStatus.SCHEDULED.value: {TaskStatus.RUNNING.value, TaskStatus.CANCELLED.value},
    TaskStatus.RUNNING.value: {
        TaskStatus.WAITING_FEEDBACK.value,
        TaskStatus.ITERATING.value,
        TaskStatus.REVIEWING.value,
        TaskStatus.SUCCESS.value,
        TaskStatus.FAILED.value,
        TaskStatus.CANCELLED.value,
        TaskStatus.TERMINATED.value,
    },
    TaskStatus.WAITING_FEEDBACK.value: {
        TaskStatus.REVIEWING.value,
        TaskStatus.RUNNING.value,
        TaskStatus.FAILED.value,
        TaskStatus.CANCELLED.value,
    },
    TaskStatus.REVIEWING.value: {
        TaskStatus.SUCCESS.value,
        TaskStatus.FAILED.value,
        TaskStatus.ITERATING.value,
        TaskStatus.RUNNING.value,
    },
    TaskStatus.ITERATING.value: {
        TaskStatus.RUNNING.value,
        TaskStatus.TERMINATED.value,
        TaskStatus.FAILED.value,
        TaskStatus.CANCELLED.value,
    },
    TaskStatus.FAILED.value: {TaskStatus.SCHEDULED.value, TaskStatus.READY.value},
    TaskStatus.SUCCESS.value: set(),
    TaskStatus.CANCELLED.value: set(),
    TaskStatus.TERMINATED.value: set(),
}


class StateMachineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def can_transition(self, from_status: str, to_status: str) -> bool:
        return to_status in TRANSITIONS.get(from_status, set())

    async def transition(
        self,
        run: TaskRun,
        to_status: str,
        *,
        actor: str = "system",
        detail: str = "",
        expected_version: int | None = None,
    ) -> TaskRun:
        if expected_version is not None and run.version != expected_version:
            raise HTTPException(status_code=409, detail="Version conflict, please refresh")

        if not self.can_transition(run.status, to_status):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transition: {run.status} -> {to_status}",
            )

        from_status = run.status
        run.status = to_status
        run.version += 1
        run.last_updated_at = datetime.now(UTC)

        if run.task:
            run.task.status = to_status

        if to_status == TaskStatus.RUNNING.value and run.started_at is None:
            run.started_at = datetime.now(UTC)

        if to_status in {TaskStatus.SUCCESS.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value, TaskStatus.TERMINATED.value}:
            run.finished_at = datetime.now(UTC)
            if to_status == TaskStatus.SUCCESS.value:
                run.progress = 100

        await write_audit(
            self.db,
            action="STATE_TRANSITION",
            target=str(run.id),
            detail=f"{from_status} -> {to_status}. {detail}",
            actor=actor,
            metadata={"from": from_status, "to": to_status, "version": run.version},
        )
        logger.info("run=%s transition %s -> %s", run.id, from_status, to_status)
        return run
