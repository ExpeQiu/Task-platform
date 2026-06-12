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
scripts/           start.sh / stop.sh / verify.sh
docs/              产品与技术文档
```

## 本地开发（无 Docker）

```bash
# 启动 postgres + redis
docker compose up -d postgres redis

# 后端
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
3. 在 `app/adapters/factory.py` 注册映射

MVP 默认 endpoint 指向本地 Simulator（Push: POST /v1/tasks，Pull: 轮询 /v1/agent/pull）。
