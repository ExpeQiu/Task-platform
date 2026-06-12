#!/usr/bin/env bash
# Seed demo data: OpenClaw + Hermes adapters and sample tasks
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.entities import AgentAdapter, AdapterProtocol, Task, TaskStatus


async def seed():
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(AgentAdapter))
        if existing.scalars().first():
            print("Seed skipped: adapters already exist")
            await db.commit()
            return

        openclaw = AgentAdapter(
            name="OpenClaw",
            adapter_type="通用智能体",
            protocol=AdapterProtocol.PUSH.value,
            endpoint=f"{os.getenv('SIMULATOR_URL', 'http://localhost:8100')}",
            description="支持复杂网页交互和数据抓取",
            is_online=True,
        )
        hermes = AgentAdapter(
            name="Hermes",
            adapter_type="私有化大模型",
            protocol=AdapterProtocol.PULL.value,
            endpoint=f"{os.getenv('SIMULATOR_URL', 'http://localhost:8100')}",
            description="用于敏感数据处理与本地逻辑推理",
            is_online=True,
        )
        db.add(openclaw)
        db.add(hermes)
        await db.flush()

        sample = Task(
            name="竞品数据监控",
            objective="抓取并分析竞品数据",
            priority=5,
            sla_seconds=300,
            tags=["demo", "monitoring"],
            agent_adapter_id=openclaw.id,
            loop_config={"max_iterations": 5, "max_duration_seconds": 3600},
            retry_config={"max_retries": 3, "backoff_base_seconds": 30},
            status=TaskStatus.DRAFT.value,
        )
        db.add(sample)
        await db.commit()
        print(f"Seed complete: OpenClaw={openclaw.id}, Hermes={hermes.id}, Task={sample.id}")


if __name__ == "__main__":
    asyncio.run(seed())
