# Agent 接入 SDK 指南

Task Platform 采用 **异步任务 + 回调** 统一协议，Agent 可通过 Push 或 Pull 两种模式接入。

## 1. 协议概览

### 平台下发（Task Dispatch）

```json
{
  "task_id": "uuid",
  "run_id": "uuid",
  "objective": "任务目标",
  "context": {},
  "constraints": { "timeout": 300, "max_tokens": 8000 },
  "callback_url": "http://localhost:8000/v1/webhooks/agent_feedback",
  "callback_auth": {
    "hmac_enabled": false,
    "signature_header": "X-Webhook-Signature",
    "algorithm": "sha256"
  }
}
```

### Agent 回调（Feedback）

```json
{
  "run_id": "uuid",
  "feedback_id": "uuid",
  "status": "success",
  "result_payload": {},
  "logs": [],
  "error_code": null
}
```

`status` 取值：`success` | `failed` | `requires_action`

## 2. Push 模式

平台 POST 至 Agent 的 `{endpoint}/v1/tasks`（Coze/Dify 可配置 `dispatch_path`）。

Agent 实现示例（FastAPI）：

```python
@app.post("/v1/tasks")
async def receive_task(payload: dict):
    asyncio.create_task(process_and_callback(payload))
    return {"accepted": True}
```

## 3. Pull 模式

Agent 轮询：

```
GET /v1/agent/pull?adapter_name={name}
Header: X-API-Key: {api_key}   # 若适配器配置了 api_key
```

无任务时返回 `null`。建议使用 `packages/agent-sdk` 中的 `AgentPullClient`。

## 4. Webhook HMAC 签名

启用 `WEBHOOK_HMAC_ENABLED=true` 后，回调需携带签名头：

```
X-Webhook-Signature: HMAC-SHA256(hex(body), secret)
```

- 全局密钥：`WEBHOOK_SECRET` 环境变量
-  per-adapter 密钥：适配器 `auth_config.webhook_secret`

Python 签名示例：

```python
import hashlib, hmac, json

body = json.dumps(payload).encode("utf-8")
sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
headers = {"X-Webhook-Signature": sig, "Content-Type": "application/json"}
```

或使用 SDK：`AgentCallbackClient(webhook_secret=..., hmac_enabled=True)`

## 5. 专用 Adapter 类型

| adapter_type | 说明 | auth_config 常用字段 |
|--------------|------|---------------------|
| `generic` | 标准 Push/Pull | `bearer_token`, `api_key` |
| `coze` / `扣子` | Coze Bot | `bot_id`, `dispatch_path` |
| `dify` | Dify Workflow | `workflow_id`, `response_mode`, `dispatch_path` |

状态映射可通过 `status_mapping` 配置，例如 Coze 的 `completed` → `success`。

## 6. 本地验证

```bash
./scripts/start.sh
./scripts/verify.sh

# Pull SDK 示例
cd packages/agent-sdk && pip install -r requirements.txt
API_BASE_URL=http://localhost:8000 PULL_ADAPTER_NAME=Hermes python -m agent_sdk.client
```

## 7. 排查清单

1. 适配器是否 Online（`/adapters` 页）
2. Push：Agent `/health` 是否可达
3. Pull：Redis 是否正常、adapter_name 是否匹配
4. 回调 401：检查 HMAC 密钥与 `X-Webhook-Signature`
5. 状态未流转：检查 `status` 值与 `status_mapping`
