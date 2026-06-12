"""DAG 结构校验 — 流程编排发布前必须通过校验。"""

import logging
from collections import defaultdict, deque

from app.schemas.dto import VALID_NODE_TYPES, WorkflowDag

logger = logging.getLogger(__name__)


def validate_dag(dag: WorkflowDag) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    nodes = dag.nodes
    edges = dag.edges
    node_ids = {n.id for n in nodes}

    if not nodes:
        errors.append("流程至少需要一个节点")
        return False, errors, warnings

    # 节点类型与 ID 唯一性
    start_nodes = [n for n in nodes if n.type == "start"]
    end_nodes = [n for n in nodes if n.type == "end"]

    if len(start_nodes) != 1:
        errors.append("必须有且仅有一个 start 节点")
    if len(end_nodes) < 1:
        errors.append("至少需要一个 end 节点")

    for node in nodes:
        if node.type not in VALID_NODE_TYPES:
            errors.append(f"节点 {node.id} 类型无效: {node.type}")
        if node.type == "agent" and not node.config.adapter_id:
            errors.append(f"Agent 节点 {node.id} 必须配置 adapter_id")
        if node.type == "condition" and not node.config.expression:
            warnings.append(f"条件节点 {node.id} 未配置 expression，将默认走 true 分支")

    # 边合法性
    for edge in edges:
        if edge.source not in node_ids:
            errors.append(f"边 {edge.id} 的 source 不存在: {edge.source}")
        if edge.target not in node_ids:
            errors.append(f"边 {edge.id} 的 target 不存在: {edge.target}")
        if edge.source == edge.target:
            errors.append(f"边 {edge.id} 不能自环")

    if errors:
        return False, errors, warnings

    # 连通性：start 可达所有节点，所有节点可达 end
    adj: dict[str, list[str]] = defaultdict(list)
    rev_adj: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adj[edge.source].append(edge.target)
        rev_adj[edge.target].append(edge.source)

    start_id = start_nodes[0].id
    reachable_from_start = _bfs(start_id, adj)
    unreachable = node_ids - reachable_from_start
    if unreachable:
        errors.append(f"以下节点无法从 start 到达: {', '.join(sorted(unreachable))}")

    end_ids = {n.id for n in end_nodes}
    for nid in node_ids - end_ids:
        reached = _bfs(nid, adj)
        if not (reached & end_ids):
            errors.append(f"节点 {nid} 无法到达任何 end 节点")

    # 环检测（条件/循环节点允许，但需有出口）
    if _has_cycle(node_ids, adj):
        warnings.append("检测到环路，请确认 loop/condition 节点有正确出口")

    valid = len(errors) == 0
    logger.info("dag validation valid=%s errors=%d warnings=%d", valid, len(errors), len(warnings))
    return valid, errors, warnings


def _bfs(start: str, adj: dict[str, list[str]]) -> set[str]:
    visited: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        cur = queue.popleft()
        if cur in visited:
            continue
        visited.add(cur)
        queue.extend(adj.get(cur, []))
    return visited


def _has_cycle(node_ids: set[str], adj: dict[str, list[str]]) -> bool:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in node_ids}

    def dfs(nid: str) -> bool:
        color[nid] = GRAY
        for nxt in adj.get(nid, []):
            if color[nxt] == GRAY:
                return True
            if color[nxt] == WHITE and dfs(nxt):
                return True
        color[nid] = BLACK
        return False

    return any(color[nid] == WHITE and dfs(nid) for nid in node_ids)
