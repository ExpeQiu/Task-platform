import csv
import io
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import AuditEvent
from app.schemas.dto import AuditEventResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventResponse])
async def list_audit(
    search: str | None = None,
    action: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditEvent)
    if search:
        query = query.where(AuditEvent.target.ilike(f"%{search}%") | AuditEvent.detail.ilike(f"%{search}%"))
    if action:
        query = query.where(AuditEvent.action == action)
    result = await db.execute(query.order_by(AuditEvent.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/export")
async def export_audit(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(1000))
    events = result.scalars().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "actor", "action", "target", "detail", "created_at"])
    for e in events:
        writer.writerow([str(e.id), e.actor, e.action, e.target, e.detail, e.created_at.isoformat()])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_export.csv"},
    )
