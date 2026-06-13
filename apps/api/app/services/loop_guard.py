import hashlib
import json
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AlertSeverity, Feedback, TaskRun
from app.services.alerts import create_alert
from app.services.audit import write_audit

logger = logging.getLogger(__name__)


def _payload_hash(payload: dict) -> str:
    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


class LoopGuard:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_before_iteration(self, run: TaskRun, loop_config: dict) -> tuple[bool, str | None]:
        max_iterations = loop_config.get("max_iterations", 10)
        max_duration = loop_config.get("max_duration_seconds", 3600)

        if run.iteration_count >= max_iterations:
            msg = f"超过最大循环次数 {max_iterations}"
            logger.warning("loop guard triggered run=%s reason=%s", run.id, msg)
            return False, msg

        if run.started_at:
            started = run.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            elapsed = (datetime.now(UTC) - started).total_seconds()
            if elapsed >= max_duration:
                msg = f"超过最大执行时长 {max_duration}s"
                logger.warning("loop guard triggered run=%s reason=%s", run.id, msg)
                return False, msg

        return True, None

    async def check_no_progress(self, run: TaskRun, loop_config: dict) -> tuple[bool, str | None]:
        threshold = loop_config.get("no_progress_threshold")
        if not threshold or threshold < 1:
            return True, None

        result = await self.db.execute(
            select(Feedback)
            .where(Feedback.run_id == run.id)
            .order_by(Feedback.received_at.desc())
            .limit(threshold)
        )
        recent = list(result.scalars().all())
        if len(recent) < threshold:
            return True, None

        hashes = [_payload_hash(fb.result_payload or {}) for fb in recent]
        if len(set(hashes)) == 1:
            msg = f"连续 {threshold} 轮无进展（result_payload 相同）"
            logger.warning("no progress detected run=%s threshold=%s", run.id, threshold)
            return False, msg

        return True, None

    def record_progress_snapshot(self, run: TaskRun, payload: dict) -> None:
        ctx = dict(run.context or {})
        snapshots = list(ctx.get("progress_snapshots") or [])
        snapshots.append(
            {
                "iteration": run.iteration_count,
                "payload_hash": _payload_hash(payload),
                "ts": datetime.now(UTC).isoformat(),
            }
        )
        ctx["progress_snapshots"] = snapshots[-20:]
        run.context = ctx

    def accumulate_budget_usage(self, run: TaskRun, result_payload: dict) -> dict:
        ctx = dict(run.context or {})
        usage = dict(ctx.get("budget_usage") or {"tokens": 0, "cost": 0.0})
        tokens = result_payload.get("tokens_used") or result_payload.get("token_usage") or 0
        cost = result_payload.get("cost") or result_payload.get("cost_usd") or 0
        try:
            usage["tokens"] = int(usage.get("tokens", 0)) + int(tokens)
        except (TypeError, ValueError):
            pass
        try:
            usage["cost"] = float(usage.get("cost", 0)) + float(cost)
        except (TypeError, ValueError):
            pass
        ctx["budget_usage"] = usage
        run.context = ctx
        logger.info("budget usage run=%s tokens=%s cost=%s", run.id, usage["tokens"], usage["cost"])
        return usage

    async def check_budget(self, run: TaskRun, loop_config: dict) -> tuple[bool, str | None]:
        limit = loop_config.get("budget_limit")
        if not limit or limit <= 0:
            return True, None
        usage = (run.context or {}).get("budget_usage") or {}
        tokens = int(usage.get("tokens", 0))
        if tokens >= int(limit):
            msg = f"超过资源预算上限 {limit}（当前 tokens={tokens}）"
            logger.warning("budget exceeded run=%s limit=%s tokens=%s", run.id, limit, tokens)
            return False, msg
        return True, None

    async def enforce_or_fail(self, run: TaskRun, loop_config: dict) -> bool:
        ok, reason = await self.check_before_iteration(run, loop_config)
        if not ok:
            await create_alert(
                self.db,
                alert_type="LoopLimitExceeded",
                content=f"{reason}, run={run.id}",
                severity=AlertSeverity.CRITICAL.value,
                run_id=run.id,
            )
            run.error_message = reason
            return False
        if not await self.enforce_budget_or_fail(run, loop_config):
            return False
        return True

    async def enforce_budget_or_fail(self, run: TaskRun, loop_config: dict) -> bool:
        ok, reason = await self.check_budget(run, loop_config)
        if ok:
            return True
        await create_alert(
            self.db,
            alert_type="BudgetExceeded",
            content=f"{reason}, run={run.id}",
            severity=AlertSeverity.WARNING.value,
            run_id=run.id,
        )
        await write_audit(
            self.db,
            action="BUDGET_EXCEEDED",
            target=str(run.id),
            detail=reason or "预算超限",
            actor="loop_guard",
        )
        run.error_message = reason
        return False

    async def enforce_no_progress_or_fail(self, run: TaskRun, loop_config: dict) -> bool:
        ok, reason = await self.check_no_progress(run, loop_config)
        if ok:
            return True
        await create_alert(
            self.db,
            alert_type="NoProgressDetected",
            content=f"{reason}, run={run.id}",
            severity=AlertSeverity.WARNING.value,
            run_id=run.id,
        )
        await write_audit(
            self.db,
            action="NO_PROGRESS_TERMINATED",
            target=str(run.id),
            detail=reason or "无进展终止",
            actor="loop_guard",
        )
        run.error_message = reason
        return False
