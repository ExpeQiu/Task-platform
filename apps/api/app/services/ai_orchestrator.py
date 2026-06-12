"""AI 流程编排 — Mock 模式 + 可选 OpenAI 接入。"""

import json
import logging
import re
from typing import Any

import httpx

from app.config import get_settings
from app.schemas.dto import AiOrchestratorResponse, DagEdge, DagNode, DagNodeConfig, WorkflowDag

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是 Task Platform 的流程编排助手。根据用户描述生成 DAG 工作流 JSON。
输出格式（仅 JSON，无 markdown）:
{
  "reply": "中文说明",
  "workflow_name": "流程名称",
  "dag": {
    "nodes": [{"id":"start","type":"start","label":"...","config":{"trigger":"webhook"},"position":{"x":0,"y":0}}],
    "edges": [{"id":"e1","source":"start","target":"..."}]
  }
}
节点 type: start | agent | end | condition | parallel | loop
agent 节点 config 含 objective，adapter_name 填 OpenClaw 或 Hermes（若适用）。
布局 position: x 间距约 180，y 间距约 120，start 在顶部居中。"""


def _find_adapter(name: str, adapter_names: list[str]) -> str | None:
    name_lower = name.lower()
    for a in adapter_names:
        if name_lower in a.lower() or a.lower() in name_lower:
            return a
    return None


def _layout_nodes(nodes: list[dict], edges: list[dict]) -> list[dict]:
    if not nodes:
        return nodes
    adj: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    in_deg: dict[str, int] = {n["id"]: 0 for n in nodes}
    for e in edges:
        adj.setdefault(e["source"], []).append(e["target"])
        in_deg[e["target"]] = in_deg.get(e["target"], 0) + 1

    layers: list[list[str]] = []
    start_ids = [n["id"] for n in nodes if n.get("type") == "start"] or [
        n["id"] for n in nodes if in_deg.get(n["id"], 0) == 0
    ]
    visited: set[str] = set()
    frontier = list(start_ids)
    while frontier:
        layers.append(frontier)
        visited.update(frontier)
        nxt: list[str] = []
        for nid in frontier:
            for t in adj.get(nid, []):
                if t not in visited and t not in nxt:
                    nxt.append(t)
        frontier = nxt

    placed = {nid for layer in layers for nid in layer}
    orphan = [n["id"] for n in nodes if n["id"] not in placed]
    if orphan:
        layers.append(orphan)

    node_map = {n["id"]: n for n in nodes}
    for yi, layer in enumerate(layers):
        for xi, nid in enumerate(layer):
            node_map[nid]["position"] = {"x": 120 + xi * 200, "y": 40 + yi * 120}
    return list(node_map.values())


def _build_dag_from_intent(message: str, adapter_names: list[str]) -> tuple[WorkflowDag, str, str]:
    msg = message.lower()
    workflow_name = "AI 生成流程"
    if "竞品" in message:
        workflow_name = "竞品分析流程"
    elif "报告" in message:
        workflow_name = "报告生成流程"
    elif "监控" in message or "告警" in message:
        workflow_name = "监控告警流程"

    want_scrape = any(k in msg for k in ("抓取", "爬取", "采集", "crawl", "scrape", "openclaw"))
    want_summarize = any(k in msg for k in ("总结", "分析", "报告", "summarize", "hermes", "摘要"))
    want_parallel = any(k in msg for k in ("并行", "同时", "parallel"))
    want_condition = any(k in msg for k in ("条件", "如果", "判断", "branch", "condition"))
    want_loop = any(k in msg for k in ("循环", "重试", "loop", "迭代"))
    want_webhook = any(k in msg for k in ("webhook", "回调", "触发"))
    want_cron = any(k in msg for k in ("定时", "cron", "周期"))

    nodes: list[dict[str, Any]] = [
        {
            "id": "start",
            "type": "start",
            "label": "定时触发" if want_cron else ("Webhook 触发" if want_webhook else "流程入口"),
            "config": {"trigger": "cron" if want_cron else ("webhook" if want_webhook else "manual")},
            "position": {"x": 250, "y": 40},
        }
    ]
    edges: list[dict[str, str]] = []
    last_targets: list[str] = ["start"]

    if want_parallel and (want_scrape or want_summarize):
        nodes.append({"id": "parallel_1", "type": "parallel", "label": "并行分发", "config": {}, "position": {"x": 250, "y": 160}})
        edges.append({"id": "e_start_par", "source": "start", "target": "parallel_1"})
        agent_ids: list[str] = []
        if want_scrape or not want_summarize:
            nodes.append({
                "id": "openclaw",
                "type": "agent",
                "label": "OpenClaw 抓取",
                "config": {"objective": "抓取并采集数据", "adapter_name": "OpenClaw"},
                "position": {"x": 80, "y": 280},
            })
            edges.append({"id": "e_par_open", "source": "parallel_1", "target": "openclaw"})
            agent_ids.append("openclaw")
        if want_summarize:
            nodes.append({
                "id": "hermes",
                "type": "agent",
                "label": "Hermes 总结",
                "config": {"objective": "生成分析报告", "adapter_name": "Hermes"},
                "position": {"x": 420, "y": 280},
            })
            edges.append({"id": "e_par_her", "source": "parallel_1", "target": "hermes"})
            agent_ids.append("hermes")
        last_targets = agent_ids
    else:
        prev = "start"
        if want_scrape:
            nodes.append({
                "id": "openclaw",
                "type": "agent",
                "label": "OpenClaw 抓取",
                "config": {"objective": "抓取目标数据", "adapter_name": "OpenClaw"},
                "position": {"x": 250, "y": 160},
            })
            edges.append({"id": "e1", "source": prev, "target": "openclaw"})
            prev = "openclaw"
        if want_summarize:
            nodes.append({
                "id": "hermes",
                "type": "agent",
                "label": "Hermes 总结",
                "config": {"objective": "生成分析总结", "adapter_name": "Hermes"},
                "position": {"x": 250, "y": 280},
            })
            edges.append({"id": "e2", "source": prev, "target": "hermes"})
            prev = "hermes"
        if not want_scrape and not want_summarize:
            nodes.append({
                "id": "agent_1",
                "type": "agent",
                "label": "Agent 执行任务",
                "config": {"objective": message[:100], "adapter_name": adapter_names[0] if adapter_names else ""},
                "position": {"x": 250, "y": 160},
            })
            edges.append({"id": "e1", "source": "start", "target": "agent_1"})
            prev = "agent_1"
        last_targets = [prev]

    join = last_targets[0]
    if want_condition:
        nodes.append({
            "id": "cond_1",
            "type": "condition",
            "label": "结果校验",
            "config": {"expression": "context.status == 'ok'"},
            "position": {"x": 250, "y": 400},
        })
        for i, t in enumerate(last_targets):
            edges.append({"id": f"e_cond_in_{i}", "source": t, "target": "cond_1"})
        join = "cond_1"

    if want_loop:
        nodes.append({
            "id": "loop_1",
            "type": "loop",
            "label": "循环重试",
            "config": {"max_iterations": 3},
            "position": {"x": 250, "y": 520},
        })
        edges.append({"id": "e_loop", "source": join, "target": "loop_1"})
        join = "loop_1"

    nodes.append({
        "id": "end",
        "type": "end",
        "label": "输出报告并告警" if "告警" in message else "流程结束",
        "config": {"action": "notify" if "告警" in message else "report"},
        "position": {"x": 250, "y": 640},
    })
    src = join if want_condition or want_loop else last_targets[0]
    edges.append({"id": "e_end", "source": src, "target": "end"})

    nodes = _layout_nodes(nodes, edges)
    dag = WorkflowDag.model_validate({"nodes": nodes, "edges": edges})

    parts = []
    if want_scrape:
        parts.append("OpenClaw 数据抓取")
    if want_summarize:
        parts.append("Hermes 智能总结")
    if want_parallel:
        parts.append("并行执行")
    if want_condition:
        parts.append("条件分支")
    if want_loop:
        parts.append("循环控制")
    summary = "、".join(parts) if parts else "基础 Agent 任务链"
    reply = f"已根据您的描述生成流程，包含：{summary}。共 {len(nodes)} 个节点、{len(edges)} 条连线。点击「应用到画布」即可预览。"
    return dag, reply, workflow_name


def _mock_chat(message: str, adapter_names: list[str]) -> AiOrchestratorResponse:
    msg = message.strip()
    if any(k in msg for k in ("帮助", "help", "怎么用", "如何")):
        return AiOrchestratorResponse(
            reply="您可以这样描述需求：\n• 「抓取竞品数据并生成分析报告」\n• 「Webhook 触发，并行执行 OpenClaw 和 Hermes」\n• 「抓取后条件判断，失败则循环重试」\n我会自动生成 DAG 并应用到画布。",
            suggestions=["抓取竞品并生成报告", "Webhook 触发并行抓取和总结", "带条件分支的数据处理流程"],
        )

    if any(k in msg for k in ("修改", "添加", "删除", "改成", "换成")) and len(msg) < 30:
        return AiOrchestratorResponse(
            reply="请具体说明要如何调整，例如「添加一个条件判断节点」或「改成并行执行 OpenClaw 和 Hermes」。我会重新生成完整流程。",
            suggestions=["添加条件分支", "改为并行执行", "增加循环重试"],
        )

    dag, reply, name = _build_dag_from_intent(msg, adapter_names)
    return AiOrchestratorResponse(reply=reply, dag=dag, workflow_name=name)


async def _llm_chat(message: str, history: list[dict], adapter_names: list[str]) -> AiOrchestratorResponse:
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set, fallback to mock")
        return _mock_chat(message, adapter_names)

    messages = [{"role": "system", "content": SYSTEM_PROMPT + f"\n可用 Agent: {', '.join(adapter_names) or '无'}"}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": message})

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"model": settings.openai_model, "messages": messages, "temperature": 0.3},
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            logger.info("ai orchestrator llm response length=%s", len(content))

        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        data = json.loads(cleaned)
        dag_data = data.get("dag")
        dag = None
        if dag_data:
            nodes = _layout_nodes(dag_data.get("nodes", []), dag_data.get("edges", []))
            dag = WorkflowDag.model_validate({"nodes": nodes, "edges": dag_data.get("edges", [])})
        return AiOrchestratorResponse(
            reply=data.get("reply", "流程已生成"),
            dag=dag,
            workflow_name=data.get("workflow_name"),
        )
    except Exception as exc:
        logger.exception("ai orchestrator llm failed: %s", exc)
        return _mock_chat(message, adapter_names)


async def chat_orchestrate(
    message: str,
    history: list[dict],
    adapter_names: list[str],
) -> AiOrchestratorResponse:
    settings = get_settings()
    logger.info("ai orchestrate mock=%s message_len=%s", settings.ai_mock_mode, len(message))
    if settings.ai_mock_mode:
        return _mock_chat(message, adapter_names)
    return await _llm_chat(message, history, adapter_names)


def bind_adapters_to_dag(dag: WorkflowDag, adapters: list[dict]) -> WorkflowDag:
    name_to_id = {a["name"]: str(a["id"]) for a in adapters}
    nodes = []
    for n in dag.nodes:
        cfg = dict(n.config.model_dump())
        adapter_name = cfg.pop("adapter_name", None)
        if adapter_name and not cfg.get("adapter_id"):
            for name, aid in name_to_id.items():
                if adapter_name.lower() in name.lower() or name.lower() in adapter_name.lower():
                    cfg["adapter_id"] = aid
                    break
        nodes.append(DagNode(id=n.id, type=n.type, label=n.label, config=DagNodeConfig(**cfg), position=n.position))
    return WorkflowDag(nodes=nodes, edges=[DagEdge(**e.model_dump()) for e in dag.edges])
