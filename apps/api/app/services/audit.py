import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AuditEvent

logger = logging.getLogger(__name__)


async def write_audit(
    db: AsyncSession,
    *,
    action: str,
    target: str,
    detail: str = "",
    actor: str = "system",
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor=actor,
        action=action,
        target=target,
        detail=detail,
        metadata_json=metadata or {},
    )
    db.add(event)
    await db.flush()
    logger.info("audit action=%s target=%s detail=%s", action, target, detail)
    return event
