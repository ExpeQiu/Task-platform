import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entities import McpServer
from app.schemas.dto import MCP_TRANSPORTS, MCP_TYPES, McpHealthResult, McpServerCreate, McpServerResponse, McpServerUpdate
from app.services.audit import write_audit
from app.services.mcp_client import probe_mcp_server

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/mcp", tags=["mcp"])


def _validate_mcp_fields(mcp_type: str | None, transport: str | None) -> None:
    if mcp_type is not None and mcp_type not in MCP_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid mcp_type, allowed: {sorted(MCP_TYPES)}")
    if transport is not None and transport not in MCP_TRANSPORTS:
        raise HTTPException(status_code=422, detail=f"Invalid transport, allowed: {sorted(MCP_TRANSPORTS)}")


@router.get("", response_model=list[McpServerResponse])
async def list_mcp_servers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(McpServer).order_by(McpServer.name))
    return result.scalars().all()


@router.post("", response_model=McpServerResponse, status_code=201)
async def create_mcp_server(payload: McpServerCreate, db: AsyncSession = Depends(get_db)):
    _validate_mcp_fields(payload.mcp_type, payload.transport)

    existing = await db.execute(select(McpServer).where(McpServer.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"MCP name '{payload.name}' already exists")

    server = McpServer(**payload.model_dump())
    db.add(server)
    await db.flush()
    await write_audit(db, action="CREATE_MCP", target=server.name, detail="新增 MCP 配置")
    logger.info("mcp created name=%s type=%s transport=%s", server.name, server.mcp_type, server.transport)
    return server


@router.get("/{mcp_id}", response_model=McpServerResponse)
async def get_mcp_server(mcp_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(McpServer).where(McpServer.id == mcp_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server


@router.patch("/{mcp_id}", response_model=McpServerResponse)
async def update_mcp_server(mcp_id: UUID, payload: McpServerUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(McpServer).where(McpServer.id == mcp_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    data = payload.model_dump(exclude_unset=True)
    _validate_mcp_fields(data.get("mcp_type"), data.get("transport"))

    if "name" in data and data["name"] != server.name:
        dup = await db.execute(select(McpServer).where(McpServer.name == data["name"]))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"MCP name '{data['name']}' already exists")

    for key, value in data.items():
        setattr(server, key, value)
    await write_audit(db, action="UPDATE_MCP", target=server.name, detail="更新 MCP 配置")
    logger.info("mcp updated name=%s", server.name)
    return server


@router.delete("/{mcp_id}", status_code=204)
async def delete_mcp_server(mcp_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(McpServer).where(McpServer.id == mcp_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    await db.delete(server)
    await write_audit(db, action="DELETE_MCP", target=server.name, detail="删除 MCP 配置")
    logger.info("mcp deleted name=%s", server.name)


@router.post("/{mcp_id}/probe", response_model=McpHealthResult)
async def probe_mcp(mcp_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(McpServer).where(McpServer.id == mcp_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    health = await probe_mcp_server(server)
    logger.info("mcp probe name=%s status=%s", server.name, health.get("status"))
    return health
