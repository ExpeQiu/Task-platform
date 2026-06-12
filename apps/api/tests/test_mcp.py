import pytest

from app.models.entities import McpServer, McpTransport, McpType
from app.services.mcp_client import _build_auth_headers, probe_mcp_server


def _make_mcp(**kwargs) -> McpServer:
    defaults = {
        "name": "TestMCP",
        "mcp_type": McpType.RAG.value,
        "transport": McpTransport.SSE.value,
        "endpoint": "http://localhost:9001/mcp",
        "description": "test",
        "auth_config": {},
        "extra_config": {},
        "is_enabled": True,
    }
    defaults.update(kwargs)
    return McpServer(**defaults)


class TestMcpAuthHeaders:
    def test_bearer_token(self):
        headers = _build_auth_headers({"bearer_token": "secret"})
        assert headers["Authorization"] == "Bearer secret"

    def test_api_key(self):
        headers = _build_auth_headers({"api_key": "key-123", "api_key_header": "X-Key"})
        assert headers["X-Key"] == "key-123"

    def test_empty(self):
        headers = _build_auth_headers({})
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"


class TestProbeMcpServer:
    @pytest.mark.asyncio
    async def test_disabled_server(self):
        server = _make_mcp(is_enabled=False)
        result = await probe_mcp_server(server)
        assert result["status"] == "Disabled"

    @pytest.mark.asyncio
    async def test_stdio_transport(self):
        server = _make_mcp(transport=McpTransport.STDIO.value)
        result = await probe_mcp_server(server)
        assert result["status"] == "Warning"
        assert "stdio" in (result.get("error") or "")

    @pytest.mark.asyncio
    async def test_unreachable_endpoint(self):
        server = _make_mcp(endpoint="http://127.0.0.1:59999/mcp")
        result = await probe_mcp_server(server)
        assert result["status"] == "Error"
