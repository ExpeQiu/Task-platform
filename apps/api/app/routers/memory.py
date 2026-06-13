import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.dto import MemoryEntryCreate, MemoryEntryResponse
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/memory", tags=["memory"])


@router.post("", response_model=MemoryEntryResponse, status_code=201)
async def create_memory_entry(payload: MemoryEntryCreate, db: AsyncSession = Depends(get_db)):
    service = MemoryService(db)
    entry = await service.save_entry(
        scope=payload.scope,
        scope_ref=payload.scope_ref,
        key=payload.key,
        content=payload.content,
        metadata=payload.metadata,
    )
    return entry


@router.get("", response_model=list[MemoryEntryResponse])
async def list_memory_entries(
    scope: str | None = None,
    scope_ref: str | None = None,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = MemoryService(db)
    return await service.list_entries(scope=scope, scope_ref=scope_ref, search=search, limit=limit)
