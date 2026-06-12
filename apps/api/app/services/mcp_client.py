"""MCP 连通性探测：向远程 MCP Server 发送 JSON-RPC initialize / tools/list 请求。"""

import logging
import time
from typing import Any

import httpx

from app.models.entities import McpServer, McpTransport

logger = logging.getLogger(__name__)

MCP_PROTOCOL_VERSION = "2024-11-05"
PROBE_TIMEOUT_SECONDS = 10.0


def _build_auth_headers(auth_config: dict) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
    bearer = auth_config.get("bearer_token")
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
        return headers
    api_key = auth_config.get("api_key")
    header_name = auth_config.get("api_key_header", "X-API-Key")
    if api_key:
        headers[header_name] = api_key
    return headers


async def _jsonrpc_call(
    client: httpx.AsyncClient,
    url: str,
    method: str,
    params: dict | None = None,
    req_id: int = 1,
) -> dict[str, Any] | None:
    payload = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        payload["params"] = params
    resp = await client.post(url, json=payload)
    if resp.status_code >= 400:
        logger.warning("mcp jsonrpc failed method=%s status=%s url=%s", method, resp.status_code, url)
        return None
    data = resp.json()
    if "error" in data:
        logger.warning("mcp jsonrpc error method=%s detail=%s", method, data["error"])
        return None
    return data.get("result")


async def probe_mcp_server(server: McpServer) -> dict:
    """探测 MCP Server 连通性，返回健康检查结果。"""
    base: dict[str, Any] = {"mcp_id": str(server.id)}

    if not server.is_enabled:
        return {**base, "status": "Disabled", "error": "MCP 已停用"}

    if server.transport == McpTransport.STDIO.value:
        return {
            **base,
            "status": "Warning",
            "error": "stdio 传输需在本地进程启动，远程无法探测",
        }

    endpoint = server.endpoint.rstrip("/")
    headers = _build_auth_headers(server.auth_config or {})
    start = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS, headers=headers) as client:
            init_result = await _jsonrpc_call(
                client,
                endpoint,
                "initialize",
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "task-platform", "version": "0.1.0"},
                },
            )
            latency_ms = round((time.monotonic() - start) * 1000, 1)

            if init_result is None:
                # 降级：仅检测 HTTP 可达性
                head_resp = await client.head(endpoint)
                if head_resp.status_code < 500:
                    return {
                        **base,
                        "status": "Warning",
                        "latency_ms": latency_ms,
                        "error": "HTTP 可达但 MCP initialize 未响应，请确认 Endpoint 与传输协议",
                    }
                return {**base, "status": "Error", "latency_ms": latency_ms, "error": "无法连接 MCP Server"}

            server_info = init_result.get("serverInfo") or {}
            protocol_version = init_result.get("protocolVersion")

            tool_count: int | None = None
            resource_count: int | None = None

            tools_result = await _jsonrpc_call(client, endpoint, "tools/list", req_id=2)
            if tools_result and isinstance(tools_result.get("tools"), list):
                tool_count = len(tools_result["tools"])

            resources_result = await _jsonrpc_call(client, endpoint, "resources/list", req_id=3)
            if resources_result and isinstance(resources_result.get("resources"), list):
                resource_count = len(resources_result["resources"])

            logger.info(
                "mcp probe ok name=%s latency_ms=%s tools=%s resources=%s",
                server.name,
                latency_ms,
                tool_count,
                resource_count,
            )
            return {
                **base,
                "status": "Connected",
                "latency_ms": latency_ms,
                "server_name": server_info.get("name"),
                "server_version": server_info.get("version"),
                "protocol_version": protocol_version,
                "tool_count": tool_count,
                "resource_count": resource_count,
            }

    except httpx.TimeoutException:
        logger.warning("mcp probe timeout name=%s endpoint=%s", server.name, endpoint)
        return {**base, "status": "Error", "error": f"连接超时（>{PROBE_TIMEOUT_SECONDS}s）"}
    except httpx.ConnectError as exc:
        logger.warning("mcp probe connect error name=%s error=%s", server.name, exc)
        return {**base, "status": "Error", "error": f"连接失败: {exc}"}
    except Exception as exc:
        logger.exception("mcp probe unexpected error name=%s", server.name)
        return {**base, "status": "Error", "error": str(exc)}
