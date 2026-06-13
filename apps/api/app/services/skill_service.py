"""Skill / Playbook 资产管理。"""

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Skill
from app.schemas.dto import SkillCreate, SkillUpdate
from app.services.audit import write_audit

logger = logging.getLogger(__name__)


class SkillService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: SkillCreate, actor: str = "admin") -> Skill:
        existing = await self.db.execute(select(Skill).where(Skill.name == payload.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Skill name already exists")
        skill = Skill(
            name=payload.name,
            description=payload.description,
            instructions=payload.instructions,
            applicable_task_types=payload.applicable_task_types,
            input_contract=payload.input_contract,
            output_contract=payload.output_contract,
            tags=payload.tags,
            is_active=payload.is_active,
        )
        self.db.add(skill)
        await self.db.flush()
        await write_audit(self.db, action="CREATE_SKILL", target=str(skill.id), detail=skill.name, actor=actor)
        logger.info("skill created id=%s name=%s", skill.id, skill.name)
        return skill

    async def get(self, skill_id: uuid.UUID) -> Skill:
        result = await self.db.execute(select(Skill).where(Skill.id == skill_id))
        skill = result.scalar_one_or_none()
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        return skill

    async def list_skills(self, *, search: str | None = None, active_only: bool = True) -> tuple[list[Skill], int]:
        query = select(Skill)
        count_q = select(func.count(Skill.id))
        if active_only:
            query = query.where(Skill.is_active.is_(True))
            count_q = count_q.where(Skill.is_active.is_(True))
        if search:
            query = query.where(Skill.name.ilike(f"%{search}%"))
            count_q = count_q.where(Skill.name.ilike(f"%{search}%"))
        total = (await self.db.execute(count_q)).scalar() or 0
        result = await self.db.execute(query.order_by(Skill.updated_at.desc()))
        return list(result.scalars().all()), total

    async def update(self, skill_id: uuid.UUID, payload: SkillUpdate, actor: str = "admin") -> Skill:
        skill = await self.get(skill_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(skill, key, value)
        await write_audit(self.db, action="UPDATE_SKILL", target=str(skill.id), detail="更新 Skill", actor=actor)
        return skill

    async def delete(self, skill_id: uuid.UUID, actor: str = "admin") -> None:
        skill = await self.get(skill_id)
        skill.is_active = False
        await write_audit(self.db, action="DELETE_SKILL", target=str(skill.id), detail="停用 Skill", actor=actor)

    def apply_to_objective(self, skill: Skill, objective: str) -> str:
        if not skill.instructions:
            return objective
        return f"{objective}\n\n[Skill: {skill.name}]\n{skill.instructions}"
