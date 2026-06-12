"""流程编排执行引擎 — 按 DAG 推进节点。"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    Task,
    TaskRun,
    TaskStatus,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowStatus,
)
from app.schemas.dto import WorkflowDag
from app.services.audit import write_audit

logger = logging.getLogger(__name__)


class WorkflowEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _parse_dag(self, wf: WorkflowDefinition) -> WorkflowDag:
        return WorkflowDag.model_validate(wf.dag)

    def _node_map(self, dag: WorkflowDag) -> dict[str, dict]:
        return {n.id: n.model_dump() for n in dag.nodes}

    def _outgoing(self, dag: WorkflowDag, node_id: str) -> list[str]:
        return [e.target for e in dag.edges if e.source == node_id]

    def _incoming(self, dag: WorkflowDag, node_id: str) -> list[str]:
        return [e.source for e in dag.edges if e.target == node_id]

    async def trigger_run(
        self,
        wf: WorkflowDefinition,
        *,
        context: dict | None = None,
        actor: str = "admin",
    ) -> WorkflowRun:
        if wf.status != WorkflowStatus.PUBLISHED.value:
            raise HTTPException(status_code=400, detail="Workflow must be published before triggering")

        dag = self._parse_dag(wf)
        start_nodes = [n for n in dag.nodes if n.type == "start"]
        if not start_nodes:
            raise HTTPException(status_code=400, detail="No start node in workflow")

        run = WorkflowRun(
            workflow_id=wf.id,
            status=WorkflowRunStatus.RUNNING.value,
            context=context or {},
            completed_nodes=[],
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        await self.db.flush()

        await write_audit(
            self.db,
            action="TRIGGER_WORKFLOW",
            target=str(run.id),
            detail=f"触发流程 {wf.name}",
            actor=actor,
            metadata={"workflow_id": str(wf.id)},
        )
        logger.info("workflow run started id=%s workflow=%s", run.id, wf.id)

        await self._advance_from_node(run, wf, dag, start_nodes[0].id)
        return run

    async def on_agent_node_complete(
        self,
        workflow_run: WorkflowRun,
        node_id: str,
        result: dict,
    ) -> None:
        wf = workflow_run.workflow
        dag = self._parse_dag(wf)

        workflow_run.context = {**workflow_run.context, f"node:{node_id}": result}
        completed = list(workflow_run.completed_nodes or [])
        if node_id not in completed:
            completed.append(node_id)
        workflow_run.completed_nodes = completed

        logger.info(
            "workflow agent node completed run=%s node=%s completed=%s",
            workflow_run.id,
            node_id,
            completed,
        )

        # 并行分支：等所有同层 agent 完成后再继续
        if not self._parallel_branch_ready(dag, completed, node_id):
            workflow_run.status = WorkflowRunStatus.WAITING_FEEDBACK.value
            return

        next_ids = self._resolve_next_nodes(dag, node_id, workflow_run.context)
        if not next_ids:
            await self._fail(workflow_run, f"No outgoing edge from node {node_id}")
            return

        workflow_run.status = WorkflowRunStatus.RUNNING.value
        for next_id in next_ids:
            await self._advance_from_node(workflow_run, wf, dag, next_id)

    async def _advance_from_node(
        self,
        run: WorkflowRun,
        wf: WorkflowDefinition,
        dag: WorkflowDag,
        node_id: str,
    ) -> None:
        nodes = self._node_map(dag)
        node = nodes.get(node_id)
        if not node:
            await self._fail(run, f"Node not found: {node_id}")
            return

        run.current_node_id = node_id
        ntype = node["type"]
        logger.info("workflow advancing run=%s node=%s type=%s", run.id, node_id, ntype)

        if ntype == "start":
            for target in self._outgoing(dag, node_id):
                await self._advance_from_node(run, wf, dag, target)
            return

        if ntype == "parallel":
            for target in self._outgoing(dag, node_id):
                await self._advance_from_node(run, wf, dag, target)
            return

        if ntype == "agent":
            await self._execute_agent_node(run, wf, node)
            return

        if ntype == "condition":
            next_ids = self._resolve_next_nodes(dag, node_id, run.context)
            for target in next_ids:
                await self._advance_from_node(run, wf, dag, target)
            return

        if ntype == "loop":
            cfg = node.get("config") or {}
            max_iter = cfg.get("max_iterations") or 3
            loop_key = f"loop:{node_id}"
            count = run.context.get(loop_key, 0)
            if count < max_iter:
                run.context = {**run.context, loop_key: count + 1}
                targets = self._outgoing(dag, node_id)
                if targets:
                    await self._advance_from_node(run, wf, dag, targets[0])
                return
            # 超出循环：走 loop 节点的第二条边（若有）
            targets = self._outgoing(dag, node_id)
            if len(targets) > 1:
                await self._advance_from_node(run, wf, dag, targets[1])
            elif targets:
                await self._advance_from_node(run, wf, dag, targets[0])
            return

        if ntype == "end":
            completed = list(run.completed_nodes or [])
            if node_id not in completed:
                completed.append(node_id)
            run.completed_nodes = completed
            run.status = WorkflowRunStatus.SUCCESS.value
            run.finished_at = datetime.now(UTC)
            run.current_node_id = node_id
            await write_audit(
                self.db,
                action="WORKFLOW_SUCCESS",
                target=str(run.id),
                detail=f"流程执行完成: {wf.name}",
            )
            logger.info("workflow run success id=%s", run.id)
            return

        await self._fail(run, f"Unknown node type: {ntype}")

    async def _execute_agent_node(self, run: WorkflowRun, wf: WorkflowDefinition, node: dict) -> None:
        cfg = node.get("config") or {}
        adapter_id = cfg.get("adapter_id")
        if not adapter_id:
            await self._fail(run, f"Agent node {node['id']} missing adapter_id")
            return

        objective = cfg.get("objective") or f"Workflow step: {node.get('label', node['id'])}"
        task = Task(
            name=f"[WF:{wf.name}] {node.get('label', node['id'])}",
            objective=objective,
            agent_adapter_id=uuid.UUID(str(adapter_id)) if isinstance(adapter_id, str) else adapter_id,
            tags=["workflow", str(wf.id)],
            status=TaskStatus.READY.value,
            loop_config={"max_iterations": 1, "max_duration_seconds": 3600},
        )
        self.db.add(task)
        await self.db.flush()

        task_run = TaskRun(
            task_id=task.id,
            workflow_run_id=run.id,
            workflow_node_id=node["id"],
            status=TaskStatus.SCHEDULED.value,
            context={**run.context, "workflow_input": run.context},
        )
        self.db.add(task_run)
        await self.db.flush()

        run.status = WorkflowRunStatus.WAITING_FEEDBACK.value
        logger.info(
            "workflow agent dispatched run=%s node=%s task_run=%s",
            run.id,
            node["id"],
            task_run.id,
        )

        from app.tasks.dispatch import dispatch_task_run

        dispatch_task_run.delay(str(task_run.id))

    def _resolve_next_nodes(self, dag: WorkflowDag, node_id: str, context: dict) -> list[str]:
        node = next((n for n in dag.nodes if n.id == node_id), None)
        if not node:
            return []

        if node.type == "condition":
            expr = (node.config.expression or "true").strip().lower()
            result = self._eval_condition(expr, context)
            edges = [e for e in dag.edges if e.source == node_id]
            if not edges:
                return []
            if result:
                return [edges[0].target]
            if len(edges) > 1:
                return [edges[1].target]
            return []

        return self._outgoing(dag, node_id)

    def _eval_condition(self, expr: str, context: dict) -> bool:
        if expr in ("true", "1", "yes"):
            return True
        if expr in ("false", "0", "no"):
            return False
        if expr.startswith("context."):
            key = expr.replace("context.", "", 1)
            val = context.get(key)
            return bool(val)
        if "==" in expr:
            left, right = [p.strip().strip("'\"") for p in expr.split("==", 1)]
            if left.startswith("context."):
                left = str(context.get(left.replace("context.", "", 1), ""))
            return left == right
        logger.warning("condition expression fallback true: %s", expr)
        return True

    def _parallel_branch_ready(self, dag: WorkflowDag, completed: list[str], finished_node: str) -> bool:
        """若 finished_node 处于并行扇出，需等同层兄弟 agent 均完成。"""
        parents = self._incoming(dag, finished_node)
        if not parents:
            return True
        parent_id = parents[0]
        parent = next((n for n in dag.nodes if n.id == parent_id), None)
        if not parent or parent.type not in ("start", "parallel"):
            return True

        sibling_agents = [
            e.target
            for e in dag.edges
            if e.source == parent_id and next((n for n in dag.nodes if n.id == e.target), None)
            and next(n for n in dag.nodes if n.id == e.target).type == "agent"
        ]
        if len(sibling_agents) <= 1:
            return True
        return all(s in completed for s in sibling_agents)

    async def _fail(self, run: WorkflowRun, message: str) -> None:
        run.status = WorkflowRunStatus.FAILED.value
        run.error_message = message
        run.finished_at = datetime.now(UTC)
        await write_audit(self.db, action="WORKFLOW_FAILED", target=str(run.id), detail=message)
        logger.error("workflow run failed id=%s error=%s", run.id, message)
