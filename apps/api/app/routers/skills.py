import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.dto import SkillCreate, SkillListResponse, SkillResponse, SkillUpdate
from app.services.skill_service import SkillService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/skills", tags=["skills"])


@router.post("", response_model=SkillResponse, status_code=201)
async def create_skill(payload: SkillCreate, db: AsyncSession = Depends(get_db)):
    service = SkillService(db)
    return await service.create(payload)


@router.get("", response_model=SkillListResponse)
async def list_skills(
    search: str | None = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    service = SkillService(db)
    items, total = await service.list_skills(search=search, active_only=active_only)
    return SkillListResponse(items=items, total=total)


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: UUID, db: AsyncSession = Depends(get_db)):
    service = SkillService(db)
    return await service.get(skill_id)


@router.patch("/{skill_id}", response_model=SkillResponse)
async def update_skill(skill_id: UUID, payload: SkillUpdate, db: AsyncSession = Depends(get_db)):
    service = SkillService(db)
    return await service.update(skill_id, payload)


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(skill_id: UUID, db: AsyncSession = Depends(get_db)):
    service = SkillService(db)
    await service.delete(skill_id)
