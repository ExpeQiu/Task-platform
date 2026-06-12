import hashlib
import hmac
import json
import logging
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.entities import Task, TaskRun

logger = logging.getLogger(__name__)
settings = get_settings()

SIGNATURE_HEADER = "X-Webhook-Signature"


def compute_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    expected = compute_signature(body, secret)
    return hmac.compare_digest(expected, signature.strip())


async def resolve_webhook_secret(db: AsyncSession, body: bytes) -> str:
    try:
        data = json.loads(body)
        run_id = data.get("run_id")
        if run_id:
            result = await db.execute(
                select(TaskRun)
                .options(selectinload(TaskRun.task).selectinload(Task.adapter))
                .where(TaskRun.id == UUID(str(run_id)))
            )
            run = result.scalar_one_or_none()
            if run and run.task and run.task.adapter:
                adapter_secret = (run.task.adapter.auth_config or {}).get("webhook_secret")
                if adapter_secret:
                    return adapter_secret
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.debug("webhook secret lookup skipped: %s", exc)
    return settings.webhook_secret


async def verify_webhook_request(request: Request, db: AsyncSession) -> bytes:
    body = await request.body()
    if not settings.webhook_hmac_enabled:
        return body

    secret = await resolve_webhook_secret(db, body)
    signature = request.headers.get(SIGNATURE_HEADER)
    if not verify_signature(body, signature, secret):
        logger.warning("webhook signature invalid header=%s", signature)
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    return body


def callback_auth_meta() -> dict:
    return {
        "hmac_enabled": settings.webhook_hmac_enabled,
        "signature_header": SIGNATURE_HEADER,
        "algorithm": "sha256",
    }
