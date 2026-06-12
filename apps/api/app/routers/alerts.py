import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import Alert, AlertStatus
from app.schemas.dto import AlertResponse, AlertUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(status: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Alert)
    if status:
        query = query.where(Alert.status == status)
    else:
        query = query.where(Alert.status.in_([AlertStatus.OPEN.value, AlertStatus.ACK.value]))
    result = await db.execute(query.order_by(Alert.created_at.desc()))
    return result.scalars().all()


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: UUID, payload: AlertUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if payload.status not in {AlertStatus.ACK.value, AlertStatus.RESOLVED.value, AlertStatus.OPEN.value}:
        raise HTTPException(status_code=400, detail="Invalid status")
    alert.status = payload.status
    if payload.status == AlertStatus.RESOLVED.value:
        alert.resolved_at = datetime.now(UTC)
    logger.info("alert updated id=%s status=%s", alert_id, payload.status)
    return alert
