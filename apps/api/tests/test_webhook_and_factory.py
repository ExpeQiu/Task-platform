import pytest

from app.adapters.coze import CozeAdapter
from app.adapters.dify import DifyAdapter
from app.adapters.factory import get_adapter
from app.models.entities import AgentAdapter, AdapterProtocol
from app.services.webhook_auth import compute_signature, verify_signature


def test_compute_and_verify_signature():
    body = b'{"run_id":"test","status":"success"}'
    secret = "my-secret"
    sig = compute_signature(body, secret)
    assert verify_signature(body, sig, secret)
    assert not verify_signature(body, "bad-sig", secret)
    assert not verify_signature(body, None, secret)


def test_factory_coze_type():
    adapter = AgentAdapter(
        name="CozeBot",
        adapter_type="coze",
        protocol=AdapterProtocol.PUSH.value,
        endpoint="http://localhost:8100",
    )
    assert isinstance(get_adapter(adapter), CozeAdapter)


def test_factory_dify_type():
    adapter = AgentAdapter(
        name="DifyFlow",
        adapter_type="dify",
        protocol=AdapterProtocol.PUSH.value,
        endpoint="http://localhost:8100",
    )
    assert isinstance(get_adapter(adapter), DifyAdapter)


def test_coze_payload_shape():
    from uuid import uuid4

    from app.models.entities import Task, TaskRun

    adapter = AgentAdapter(
        name="Coze",
        adapter_type="coze",
        protocol=AdapterProtocol.PUSH.value,
        endpoint="http://localhost:8100",
        auth_config={"bot_id": "bot-123"},
    )
    impl = CozeAdapter(adapter)
    task = Task(id=uuid4(), objective="analyze data", sla_seconds=300)
    run = TaskRun(id=uuid4(), context={"conversation_id": "c1"})
    payload = impl.build_payload(run, task)
    assert payload["coze"]["bot_id"] == "bot-123"
    assert payload["input"] == "analyze data"
    assert "callback_auth" in payload


def test_dify_normalize_succeeded():
    adapter = AgentAdapter(name="D", adapter_type="dify", endpoint="http://x", protocol="push")
    assert DifyAdapter(adapter).normalize_status("succeeded") == "success"
