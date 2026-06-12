import pytest

from app.adapters.base import PushAdapter, PullAdapter
from app.models.entities import AgentAdapter, AdapterProtocol


def _make_adapter(**kwargs) -> AgentAdapter:
    defaults = {
        "name": "TestAgent",
        "adapter_type": "generic",
        "protocol": AdapterProtocol.PUSH.value,
        "endpoint": "http://localhost:8100",
        "description": "",
        "auth_config": {},
        "status_mapping": {},
        "is_online": True,
    }
    defaults.update(kwargs)
    return AgentAdapter(**defaults)


class TestBaseAgentAdapter:
    def test_build_auth_headers_bearer(self):
        adapter = _make_adapter(auth_config={"bearer_token": "secret123"})
        headers = PushAdapter(adapter).build_auth_headers()
        assert headers == {"Authorization": "Bearer secret123"}

    def test_build_auth_headers_api_key(self):
        adapter = _make_adapter(auth_config={"api_key": "key-abc", "api_key_header": "X-Custom-Key"})
        headers = PushAdapter(adapter).build_auth_headers()
        assert headers == {"X-Custom-Key": "key-abc"}

    def test_build_auth_headers_empty(self):
        adapter = _make_adapter()
        assert PushAdapter(adapter).build_auth_headers() == {}

    def test_normalize_status_with_mapping(self):
        adapter = _make_adapter(status_mapping={"completed": "success", "ERROR": "failed"})
        impl = PushAdapter(adapter)
        assert impl.normalize_status("completed") == "success"
        assert impl.normalize_status("ERROR") == "failed"
        assert impl.normalize_status("running") == "running"

    def test_build_payload_contains_callback_url(self):
        from uuid import uuid4

        from app.models.entities import Task, TaskRun

        adapter = _make_adapter()
        impl = PushAdapter(adapter)
        task = Task(id=uuid4(), objective="test objective", sla_seconds=300)
        run = TaskRun(id=uuid4(), context={"key": "val"})
        payload = impl.build_payload(run, task)
        assert payload["objective"] == "test objective"
        assert "/v1/webhooks/agent_feedback" in payload["callback_url"]
        assert payload["context"] == {"key": "val"}


class TestPullAdapter:
    @pytest.mark.asyncio
    async def test_health_check_requires_redis(self):
        adapter = _make_adapter(name="Hermes", protocol=AdapterProtocol.PULL.value)
        result = await PullAdapter(adapter).health_check()
        assert result["protocol"] == "pull"
        assert "pull_url" in result
        assert result["status"] in {"ok", "error"}
