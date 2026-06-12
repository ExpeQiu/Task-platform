import hashlib
import hmac
import json
import logging
import os
import uuid
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SIGNATURE_HEADER = "X-Webhook-Signature"


def compute_webhook_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def build_callback_headers(body: bytes, secret: str, hmac_enabled: bool) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if hmac_enabled and secret:
        headers[SIGNATURE_HEADER] = compute_webhook_signature(body, secret)
    return headers


class AgentPullClient:
    """Pull 模式 Agent 客户端：轮询平台任务队列。"""

    def __init__(
        self,
        api_base_url: str,
        adapter_name: str,
        *,
        api_key: str | None = None,
        poll_interval: float = 3.0,
        timeout: float = 10.0,
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.adapter_name = adapter_name
        self.api_key = api_key
        self.poll_interval = poll_interval
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        if self.api_key:
            return {"X-API-Key": self.api_key}
        return {}

    async def pull_once(self) -> dict[str, Any] | None:
        url = f"{self.api_base_url}/v1/agent/pull"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                params={"adapter_name": self.adapter_name},
                headers=self._headers(),
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            if not resp.text or resp.text == "null":
                return None
            data = resp.json()
            return data if data else None

    async def poll_forever(self, handler):
        """handler: async callable(task: dict) -> None"""
        import asyncio

        logger.info("pull client started adapter=%s interval=%s", self.adapter_name, self.poll_interval)
        while True:
            try:
                task = await self.pull_once()
                if task:
                    await handler(task)
            except Exception as exc:
                logger.warning("pull error adapter=%s error=%s", self.adapter_name, exc)
            await asyncio.sleep(self.poll_interval)


class AgentCallbackClient:
    """Agent 回调客户端：向平台上报执行结果。"""

    def __init__(self, webhook_secret: str = "", hmac_enabled: bool = False):
        self.webhook_secret = webhook_secret
        self.hmac_enabled = hmac_enabled

    async def send_feedback(
        self,
        callback_url: str,
        *,
        run_id: str,
        status: str,
        result_payload: dict | None = None,
        logs: list | None = None,
        error_code: str | None = None,
        feedback_id: str | None = None,
    ) -> dict:
        payload = {
            "run_id": run_id,
            "feedback_id": feedback_id or str(uuid.uuid4()),
            "status": status,
            "result_payload": result_payload or {},
            "logs": logs or [],
            "error_code": error_code,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = build_callback_headers(body, self.webhook_secret, self.hmac_enabled)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(callback_url, content=body, headers=headers)
            resp.raise_for_status()
            return resp.json()


async def run_pull_agent_example():
    """示例：Pull Agent 主循环。"""
    import asyncio

    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    adapter_name = os.getenv("PULL_ADAPTER_NAME", "Hermes")
    webhook_secret = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret-change-me")
    hmac_enabled = os.getenv("WEBHOOK_HMAC_ENABLED", "false").lower() == "true"
    api_key = os.getenv("PULL_API_KEY")

    pull = AgentPullClient(api_url, adapter_name, api_key=api_key)
    callback = AgentCallbackClient(webhook_secret=webhook_secret, hmac_enabled=hmac_enabled)

    async def handle(task: dict):
        run_id = task["run_id"]
        objective = task.get("objective", "")
        logger.info("processing run_id=%s objective=%s", run_id, objective[:80])
        await asyncio.sleep(1)
        await callback.send_feedback(
            task["callback_url"],
            run_id=run_id,
            status="success",
            result_payload={"summary": f"Done: {objective[:50]}"},
            logs=[{"level": "info", "message": "SDK example completed"}],
        )

    await pull.poll_forever(handle)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import asyncio

    asyncio.run(run_pull_agent_example())
