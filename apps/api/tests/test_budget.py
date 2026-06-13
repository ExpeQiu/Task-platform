import pytest
from uuid import uuid4

from app.services.loop_guard import LoopGuard


class _Run:
    def __init__(self):
        self.id = uuid4()
        self.context = {}


@pytest.mark.asyncio
async def test_budget_accumulate_and_exceed():
    guard = LoopGuard(db=None)  # type: ignore
    run = _Run()
    guard.accumulate_budget_usage(run, {"tokens_used": 500})
    guard.accumulate_budget_usage(run, {"tokens_used": 600})
    ok, reason = await guard.check_budget(run, {"budget_limit": 1000})
    assert ok is False
    assert reason and "1000" in reason


@pytest.mark.asyncio
async def test_budget_null_limit_skips():
    guard = LoopGuard(db=None)  # type: ignore
    run = _Run()
    guard.accumulate_budget_usage(run, {"tokens_used": 9999})
    ok, _ = await guard.check_budget(run, {"budget_limit": None})
    assert ok is True
