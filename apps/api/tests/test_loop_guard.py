import pytest
from uuid import uuid4

from app.services.loop_guard import _payload_hash


def test_payload_hash_stable():
    payload = {"a": 1, "b": "test"}
    assert _payload_hash(payload) == _payload_hash({"b": "test", "a": 1})


def test_payload_hash_differs():
    assert _payload_hash({"x": 1}) != _payload_hash({"x": 2})


def test_no_progress_threshold_null_skips():
    import asyncio

    from app.services.loop_guard import LoopGuard

    class _Run:
        id = uuid4()
        iteration_count = 1
        started_at = None
        context = {}

    guard = LoopGuard(db=None)  # type: ignore

    async def _check():
        ok, reason = await guard.check_no_progress(_Run(), {"no_progress_threshold": None})
        assert ok is True
        assert reason is None

    asyncio.run(_check())
