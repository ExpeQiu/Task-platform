import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.factory import get_adapter
from app.database import get_db
from app.models.entities import AgentAdapter
from app.schemas.dto import AdapterCreate, AdapterResponse, AdapterUpdate
from app.services.audit import write_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/adapters", tags=["adapters"])


@router.get("", response_model=list[AdapterResponse])
async def list_adapters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentAdapter).order_by(AgentAdapter.name))
    return result.scalars().all()


@router.post("", response_model=AdapterResponse, status_code=201)
async def create_adapter(payload: AdapterCreate, db: AsyncSession = Depends(get_db)):
    adapter = AgentAdapter(**payload.model_dump())
    db.add(adapter)
    await db.flush()
    await write_audit(db, action="CREATE_ADAPTER", target=adapter.name, detail="新增适配器")
    return adapter


@router.get("/{adapter_id}", response_model=AdapterResponse)
async def get_adapter_detail(adapter_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentAdapter).where(AgentAdapter.id == adapter_id))
    adapter = result.scalar_one_or_none()
    if not adapter:
        raise HTTPException(status_code=404, detail="Adapter not found")
    return adapter


@router.patch("/{adapter_id}", response_model=AdapterResponse)
async def update_adapter(adapter_id: UUID, payload: AdapterUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentAdapter).where(AgentAdapter.id == adapter_id))
    adapter = result.scalar_one_or_none()
    if not adapter:
        raise HTTPException(status_code=404, detail="Adapter not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(adapter, key, value)
    await write_audit(db, action="UPDATE_ADAPTER", target=adapter.name, detail="更新适配器")
    return adapter


@router.get("/{adapter_id}/health")
async def adapter_health(adapter_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentAdapter).where(AgentAdapter.id == adapter_id))
    adapter = result.scalar_one_or_none()
    if not adapter:
        raise HTTPException(status_code=404, detail="Adapter not found")
    impl = get_adapter(adapter)
    health = await impl.health_check()
    return {"adapter_id": str(adapter_id), **health, "is_online": adapter.is_online}
