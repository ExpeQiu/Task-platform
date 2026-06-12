"""DAG 校验单元测试"""

from uuid import uuid4

from app.schemas.dto import DagEdge, DagNode, DagNodeConfig, WorkflowDag
from app.services.dag_validator import validate_dag


def _minimal_dag() -> WorkflowDag:
    adapter_id = uuid4()
    nodes = [
        DagNode(id="start", type="start", label="Start", config=DagNodeConfig(trigger="webhook")),
        DagNode(
            id="agent1",
            type="agent",
            label="Agent",
            config=DagNodeConfig(adapter_id=adapter_id, objective="do work"),
        ),
        DagNode(id="end", type="end", label="End", config=DagNodeConfig(action="notify")),
    ]
    edges = [
        DagEdge(id="e1", source="start", target="agent1"),
        DagEdge(id="e2", source="agent1", target="end"),
    ]
    return WorkflowDag(nodes=nodes, edges=edges)


def test_valid_minimal_dag():
    valid, errors, _ = validate_dag(_minimal_dag())
    assert valid is True
    assert errors == []


def test_missing_start():
    dag = _minimal_dag()
    dag.nodes = [n for n in dag.nodes if n.type != "start"]
    valid, errors, _ = validate_dag(dag)
    assert valid is False
    assert any("start" in e for e in errors)


def test_agent_without_adapter():
    dag = _minimal_dag()
    dag.nodes = [
        DagNode(id="start", type="start", label="Start"),
        DagNode(id="agent1", type="agent", label="Agent", config=DagNodeConfig()),
        DagNode(id="end", type="end", label="End"),
    ]
    valid, errors, _ = validate_dag(dag)
    assert valid is False
    assert any("adapter_id" in e for e in errors)


def test_unreachable_node():
    dag = _minimal_dag()
    dag.nodes.append(DagNode(id="orphan", type="end", label="Orphan"))
    valid, errors, _ = validate_dag(dag)
    assert valid is False
    assert any("orphan" in e.lower() or "无法从 start" in e for e in errors)
