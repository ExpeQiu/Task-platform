# Agent SDK

Python 客户端，用于 Pull 模式 Agent 接入 Task Platform。

## 安装

```bash
cd packages/agent-sdk
pip install -r requirements.txt
```

## 快速开始（Pull 模式）

```python
import asyncio
from agent_sdk import AgentPullClient, AgentCallbackClient

async def main():
    pull = AgentPullClient("http://localhost:8000", "Hermes", api_key="your-key")
    callback = AgentCallbackClient(webhook_secret="dev-webhook-secret-change-me", hmac_enabled=False)

    task = await pull.pull_once()
    if task:
        await callback.send_feedback(
            task["callback_url"],
            run_id=task["run_id"],
            status="success",
            result_payload={"summary": "done"},
        )

asyncio.run(main())
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `API_BASE_URL` | 平台 API 地址 |
| `PULL_ADAPTER_NAME` | 适配器名称 |
| `PULL_API_KEY` | Pull 鉴权 Key（适配器 auth_config.api_key） |
| `WEBHOOK_SECRET` | 回调 HMAC 密钥 |
| `WEBHOOK_HMAC_ENABLED` | 是否启用回调签名 |

## 运行示例

```bash
API_BASE_URL=http://localhost:8000 PULL_ADAPTER_NAME=Hermes python -m agent_sdk.client
```

详细协议见 [docs/agent-sdk.md](../../docs/agent-sdk.md)。
