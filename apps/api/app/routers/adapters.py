import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.factory import get_adapter
from app.database import get_db
from app.models.entities import AgentAdapter, Assignment, Task
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
    existing = await db.execute(select(AgentAdapter).where(AgentAdapter.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Adapter name '{payload.name}' already exists")

    adapter = AgentAdapter(**payload.model_dump())
    db.add(adapter)
    await db.flush()
    await write_audit(db, action="CREATE_ADAPTER", target=adapter.name, detail="新增适配器")
    logger.info("adapter created name=%s protocol=%s", adapter.name, adapter.protocol)
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

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != adapter.name:
        dup = await db.execute(select(AgentAdapter).where(AgentAdapter.name == data["name"]))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Adapter name '{data['name']}' already exists")

    for key, value in data.items():
        setattr(adapter, key, value)
    await write_audit(db, action="UPDATE_ADAPTER", target=adapter.name, detail="更新适配器")
    logger.info("adapter updated name=%s", adapter.name)
    return adapter


@router.delete("/{adapter_id}", status_code=204)
async def delete_adapter(adapter_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentAdapter).where(AgentAdapter.id == adapter_id))
    adapter = result.scalar_one_or_none()
    if not adapter:
        raise HTTPException(status_code=404, detail="Adapter not found")

    task_count = (
        await db.execute(select(func.count(Task.id)).where(Task.agent_adapter_id == adapter_id))
    ).scalar() or 0
    if task_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Adapter is referenced by {task_count} task(s); disable it instead of deleting",
        )

    await db.delete(adapter)
    await write_audit(db, action="DELETE_ADAPTER", target=adapter.name, detail="删除适配器")
    logger.info("adapter deleted name=%s", adapter.name)


@router.get("/{adapter_id}/health")
async def adapter_health(adapter_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentAdapter).where(AgentAdapter.id == adapter_id))
    adapter = result.scalar_one_or_none()
    if not adapter:
        raise HTTPException(status_code=404, detail="Adapter not found")

    assignment_count = (
        await db.execute(select(func.count(Assignment.id)).where(Assignment.adapter_id == adapter_id))
    ).scalar() or 0

    impl = get_adapter(adapter)
    health = await impl.health_check()
    return {
        "adapter_id": str(adapter_id),
        **health,
        "is_online": adapter.is_online,
        "assignment_count": assignment_count,
    }
