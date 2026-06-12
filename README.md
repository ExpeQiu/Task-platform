# Task Platform

任务编排中心 MVP — 统一调度 OpenClaw / Hermes 等 Agent，维护任务状态机、调度、告警与审计。

## 快速启动

```bash
cp .env.example .env
chmod +x scripts/*.sh
./scripts/start.sh
./scripts/verify.sh
```

- API: http://localhost:8000/docs
- Web: http://localhost:3000
- Simulator: http://localhost:8100/health

## 目录结构

```
apps/api/          FastAPI 后端
apps/web/          Next.js 前端
packages/agent-simulator/  Agent Mock 模拟器
packages/agent-sdk/        Pull/回调 Python SDK
scripts/           start.sh / stop.sh / verify.sh
docs/              产品与技术文档（含 docs/agent-sdk.md）
```

## 本地开发

默认使用 **本机 Homebrew** 的 PostgreSQL@17 与 Redis，不再依赖 Docker 启动数据库。

```bash
# 首次：安装并启动本地服务
brew install postgresql@17 redis
brew services start postgresql@17
brew services start redis

# 一键本地开发（API/Worker/Simulator 进程 + Web）
cp .env.example .env
chmod +x scripts/*.sh
./scripts/dev-local.sh

# 或 Docker 运行应用层，数据库仍走本机
./scripts/start.sh
```

`.env` 中连接串指向 `localhost:5432` / `localhost:6379`。Docker 模式由 `start.sh` 自动改写为 `host.docker.internal`。

如需改回 Docker 版 Postgres/Redis：`docker compose --profile docker-infra up -d postgres redis`

## 本地开发（手动分进程）
cd apps/api && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Celery
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info

# Simulator
cd packages/agent-simulator && pip install -r requirements.txt
python -m simulator.main

# 前端
cd apps/web && npm install && npm run dev
```

## Mock / 真实 Adapter 切换

1. 在 Agent 接入页修改 Adapter 的 `endpoint` 与鉴权配置
2. 实现 `app/adapters/base.py` 中的 `BaseAgentAdapter` 子类
3. 在 `app/adapters/factory.py` 注册映射（已内置 coze / dify）

MVP 默认 endpoint 指向本地 Simulator（Push: POST /v1/tasks，Pull: 轮询 /v1/agent/pull）。

## Webhook HMAC

`.env` 中设置 `WEBHOOK_HMAC_ENABLED=true` 后，Agent 回调需携带 `X-Webhook-Signature` 头。Simulator 与 SDK 均支持该配置。

## Agent SDK

Pull 模式接入见 `packages/agent-sdk` 与 `docs/agent-sdk.md`。
