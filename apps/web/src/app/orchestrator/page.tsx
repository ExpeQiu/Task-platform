"use client";

import { AppShell } from "@/components/layout/app-shell";
import { DagCanvas, DEFAULT_DAG, NODE_PALETTE, newEdgeId, newNodeId } from "@/components/orchestrator/dag-canvas";
import { AiOrchestratorButton, AiOrchestratorPanel } from "@/components/orchestrator/ai-panel";
import { NodePanel, PaletteItem } from "@/components/orchestrator/node-panel";
import {
  Adapter,
  api,
  DagEdge,
  DagNode,
  NodeType,
  Workflow,
  WorkflowDag,
  WorkflowRun,
} from "@/lib/api";
import { useCallback, useEffect, useState } from "react";

const STATUS_BADGE: Record<string, string> = {
  Draft: "bg-gray-100 text-gray-700",
  Published: "bg-green-100 text-green-700",
  Archived: "bg-yellow-100 text-yellow-700",
  PendingApproval: "bg-rose-100 text-rose-800",
  Running: "bg-blue-100 text-blue-800",
  Success: "bg-green-100 text-green-800",
  Failed: "bg-red-100 text-red-800",
};

export default function OrchestratorPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [current, setCurrent] = useState<Workflow | null>(null);
  const [dag, setDag] = useState<WorkflowDag>(DEFAULT_DAG);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [adapters, setAdapters] = useState<Adapter[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<Awaited<ReturnType<typeof api.listRunApprovals>>>([]);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [showRuns, setShowRuns] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const [aiOpen, setAiOpen] = useState(false);

  const handleSelectNode = (id: string | null) => {
    setSelectedId(id);
    if (id) {
      setPanelOpen(true);
    } else {
      setPanelOpen(false);
    }
  };

  const flash = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(""), 3000);
  };

  const loadList = useCallback(() => {
    api.listWorkflows().then((r) => setWorkflows(r.items)).catch(() => flash("加载流程列表失败"));
    api.listAdapters().then(setAdapters).catch(() => {});
  }, []);

  useEffect(() => {
    loadList();
  }, [loadList]);

  // 默认 DAG 中按名称自动匹配 Agent 适配器
  useEffect(() => {
    if (!adapters.length) return;
    setDag((prev) => ({
      ...prev,
      nodes: prev.nodes.map((n) => {
        if (n.type !== "agent" || n.config.adapter_id) return n;
        const match = adapters.find(
          (a) =>
            n.label.toLowerCase().includes(a.name.toLowerCase()) ||
            a.name.toLowerCase().includes(n.id.replace("_", ""))
        );
        return match ? { ...n, config: { ...n.config, adapter_id: match.id } } : n;
      }),
    }));
  }, [adapters]);

  const openRunDetail = async (run: WorkflowRun) => {
    setExpandedRunId(run.id === expandedRunId ? null : run.id);
    if (run.status === "PendingApproval") {
      const approvals = await api.listRunApprovals(run.id);
      setPendingApprovals(approvals);
    }
  };

  const decideApproval = async (runId: string, approvalId: string, approved: boolean) => {
    await api.decideApproval(runId, approvalId, { approved });
    flash(approved ? "审批已通过" : "审批已拒绝");
    if (current) api.listWorkflowRuns(current.id).then(setRuns);
    setPendingApprovals([]);
  };

  const selectWorkflow = (wf: Workflow) => {
    setCurrent(wf);
    setDag(wf.dag?.nodes?.length ? wf.dag : DEFAULT_DAG);
    setSelectedId(null);
    api.listWorkflowRuns(wf.id).then(setRuns).catch(() => setRuns([]));
  };

  const createNew = async () => {
    setLoading(true);
    try {
      const wf = await api.createWorkflow({ name: `新流程 ${workflows.length + 1}`, dag: DEFAULT_DAG });
      loadList();
      selectWorkflow(wf);
      flash("已创建新流程草稿");
    } catch (e) {
      flash(e instanceof Error ? e.message : "创建失败");
    } finally {
      setLoading(false);
    }
  };

  const saveDraft = async () => {
    if (!current) return flash("请先选择或创建流程");
    setLoading(true);
    try {
      const updated = await api.updateWorkflow(current.id, { dag, name: current.name, description: current.description });
      setCurrent(updated);
      loadList();
      flash("草稿已保存");
    } catch (e) {
      flash(e instanceof Error ? e.message : "保存失败");
    } finally {
      setLoading(false);
    }
  };

  const validate = async () => {
    if (!current) return flash("请先选择流程");
    if (current.status === "Draft") await saveDraft();
    try {
      const result = await api.validateWorkflow(current!.id);
      if (result.valid) {
        flash(`校验通过${result.warnings.length ? `（${result.warnings.length} 条警告）` : ""}`);
      } else {
        flash(`校验失败: ${result.errors.join("; ")}`);
      }
    } catch (e) {
      flash(e instanceof Error ? e.message : "校验失败");
    }
  };

  const publish = async () => {
    if (!current) return flash("请先选择流程");
    setLoading(true);
    try {
      await saveDraft();
      const updated = await api.publishWorkflow(current.id);
      setCurrent(updated);
      loadList();
      flash(`流程已发布 v${updated.version}`);
    } catch (e) {
      flash(e instanceof Error ? e.message : "发布失败");
    } finally {
      setLoading(false);
    }
  };

  const trigger = async () => {
    if (!current) return flash("请先选择流程");
    if (current.status !== "Published") return flash("请先发布流程");
    setLoading(true);
    try {
      const run = await api.triggerWorkflow(current.id);
      flash(`已触发执行 run=${run.id.slice(0, 8)}…`);
      api.listWorkflowRuns(current.id).then(setRuns);
      setShowRuns(true);
    } catch (e) {
      flash(e instanceof Error ? e.message : "触发失败");
    } finally {
      setLoading(false);
    }
  };

  const addNode = (type: NodeType) => {
    const palette = NODE_PALETTE.find((p) => p.type === type);
    const id = newNodeId(type, dag.nodes);
    const node: DagNode = {
      id,
      type,
      label: palette?.defaultLabel || type,
      config: type === "start" ? { trigger: "webhook" } : type === "end" ? { action: "notify" } : type === "approval" ? { title: "人工审批", message: "" } : {},
      position: { x: 80 + dag.nodes.length * 30, y: 80 + dag.nodes.length * 20 },
    };
    setDag({ ...dag, nodes: [...dag.nodes, node] });
    setSelectedId(id);
    setPanelOpen(true);
  };

  const updateNode = (node: DagNode) => {
    setDag({ ...dag, nodes: dag.nodes.map((n) => (n.id === node.id ? node : n)) });
  };

  const deleteNode = (id: string) => {
    setDag({
      nodes: dag.nodes.filter((n) => n.id !== id),
      edges: dag.edges.filter((e) => e.source !== id && e.target !== id),
    });
    if (selectedId === id) setSelectedId(null);
  };

  const addEdge = (source: string, target: string) => {
    if (dag.edges.some((e) => e.source === source && e.target === target)) return;
    setDag({ ...dag, edges: [...dag.edges, { id: newEdgeId(dag.edges), source, target }] });
  };

  const removeEdge = (edgeId: string) => {
    setDag({ ...dag, edges: dag.edges.filter((e) => e.id !== edgeId) });
  };

  const moveNode = (id: string, x: number, y: number) => {
    setDag({ ...dag, nodes: dag.nodes.map((n) => (n.id === id ? { ...n, position: { x, y } } : n)) });
  };

  const selectedNode = dag.nodes.find((n) => n.id === selectedId) || null;
  const isDraft = !current || current.status === "Draft";

  const applyAiDag = async (newDag: WorkflowDag, workflowName?: string) => {
    setDag(newDag);
    setSelectedId(null);
    setPanelOpen(false);
    if (current && isDraft) {
      setCurrent({ ...current, name: workflowName || current.name });
      flash("AI 流程已应用到画布");
      return;
    }
    setLoading(true);
    try {
      const wf = await api.createWorkflow({
        name: workflowName || `AI 流程 ${workflows.length + 1}`,
        dag: newDag,
      });
      loadList();
      setCurrent(wf);
      setDag(newDag);
      flash("已创建 AI 流程并应用到画布");
    } catch (e) {
      flash(e instanceof Error ? e.message : "应用失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell title="流程编排">
      <div className="h-full flex flex-col gap-4 min-h-[600px]">
        {message && (
          <div className="px-4 py-2 bg-indigo-50 text-indigo-800 text-sm rounded-md border border-indigo-100">{message}</div>
        )}

        <div className="flex flex-1 gap-0 bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden min-h-[520px]">
          {/* 流程列表 */}
          <div className="w-52 border-r bg-gray-50 flex flex-col">
            <div className="px-3 py-3 border-b flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700">流程列表</span>
              <button
                type="button"
                onClick={createNew}
                disabled={loading}
                className="text-xs bg-indigo-600 text-white px-2 py-1 rounded hover:bg-indigo-700 disabled:opacity-50"
              >
                新建
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {workflows.length === 0 && <p className="text-xs text-gray-400 p-2">暂无流程，点击新建</p>}
              {workflows.map((wf) => (
                <button
                  key={wf.id}
                  type="button"
                  onClick={() => selectWorkflow(wf)}
                  className={`w-full text-left px-2 py-2 rounded text-sm ${current?.id === wf.id ? "bg-indigo-100 text-indigo-900" : "hover:bg-gray-100"}`}
                >
                  <div className="font-medium truncate">{wf.name}</div>
                  <div className="flex items-center gap-1 mt-0.5">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${STATUS_BADGE[wf.status] || STATUS_BADGE.Draft}`}>{wf.status}</span>
                    <span className="text-xs text-gray-400">v{wf.version}</span>
                  </div>
                </button>
              ))}
            </div>
            {isDraft && (
              <div className="p-2 border-t space-y-1">
                <p className="text-xs text-gray-500 px-1 mb-1">添加节点</p>
                {NODE_PALETTE.map((p) => (
                  <PaletteItem key={p.type} type={p.type} label={p.label} onAdd={addNode} />
                ))}
              </div>
            )}
          </div>

          {/* 画布区 */}
          <div className="flex-1 flex flex-col min-w-0 relative">
            <div className="px-4 py-3 border-b flex justify-between items-center bg-gray-50 gap-2 flex-wrap">
              <div>
                <h3 className="text-base font-medium text-gray-800">
                  {current ? current.name : "流程设计器 (DAG)"}
                </h3>
                {current && (
                  <input
                    className="mt-1 text-sm border border-gray-300 rounded px-2 py-0.5 w-64"
                    value={current.name}
                    disabled={!isDraft}
                    onChange={(e) => setCurrent({ ...current, name: e.target.value })}
                  />
                )}
              </div>
              <div className="flex gap-2 flex-wrap items-center">
                <AiOrchestratorButton onClick={() => { setPanelOpen(false); setAiOpen(true); }} disabled={loading} />
                <button
                  type="button"
                  onClick={saveDraft}
                  disabled={!current || !isDraft || loading}
                  className="bg-white border border-gray-300 text-gray-700 px-3 py-1.5 rounded-md text-sm hover:bg-gray-50 disabled:opacity-50"
                >
                  保存草稿
                </button>
                <button
                  type="button"
                  onClick={validate}
                  disabled={!current || loading}
                  className="bg-white border border-gray-300 text-gray-700 px-3 py-1.5 rounded-md text-sm hover:bg-gray-50 disabled:opacity-50"
                >
                  校验
                </button>
                <button
                  type="button"
                  onClick={publish}
                  disabled={!current || !isDraft || loading}
                  className="bg-indigo-600 text-white px-3 py-1.5 rounded-md text-sm hover:bg-indigo-700 disabled:opacity-50"
                >
                  发布流程
                </button>
                <button
                  type="button"
                  onClick={trigger}
                  disabled={!current || current?.status !== "Published" || loading}
                  className="bg-green-600 text-white px-3 py-1.5 rounded-md text-sm hover:bg-green-700 disabled:opacity-50"
                >
                  触发执行
                </button>
                {current && (
                  <button
                    type="button"
                    onClick={() => setShowRuns(!showRuns)}
                    className="text-sm text-indigo-600 hover:underline px-2"
                  >
                    运行记录 ({runs.length})
                  </button>
                )}
              </div>
            </div>

            <div className="flex flex-1 min-h-0 relative">
              <DagCanvas
                nodes={dag.nodes}
                edges={dag.edges}
                selectedId={selectedId}
                onSelect={handleSelectNode}
                onMoveNode={moveNode}
              />
              {isDraft && (
                <>
                  <button
                    type="button"
                    onClick={() => setPanelOpen((v) => !v)}
                    className="absolute right-0 top-1/2 -translate-y-1/2 z-20 bg-white border border-gray-200 rounded-l-md px-1 py-3 text-xs text-gray-500 hover:bg-gray-50 shadow-sm"
                    title={panelOpen ? "收起属性面板" : "展开属性面板"}
                  >
                    {panelOpen ? "›" : "‹"}
                  </button>
                  {panelOpen && (
                    <NodePanel
                      node={selectedNode}
                      nodes={dag.nodes}
                      edges={dag.edges}
                      adapters={adapters}
                      onChange={updateNode}
                      onDelete={deleteNode}
                      onAddEdge={addEdge}
                      onRemoveEdge={removeEdge}
                      onClose={() => setPanelOpen(false)}
                    />
                  )}
                </>
              )}
            </div>

            <AiOrchestratorPanel
              open={aiOpen}
              onClose={() => setAiOpen(false)}
              adapters={adapters}
              currentDag={dag}
              onApply={applyAiDag}
            />
          </div>
        </div>

        {showRuns && runs.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="text-sm font-medium mb-2">最近运行记录</h4>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="py-2 pr-4">Run ID</th>
                    <th className="py-2 pr-4">状态</th>
                    <th className="py-2 pr-4">当前节点</th>
                    <th className="py-2 pr-4">开始时间</th>
                    <th className="py-2">错误</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => (
                    <tr
                      key={r.id}
                      className={`border-b border-gray-50 cursor-pointer hover:bg-gray-50 ${r.status === "PendingApproval" ? "bg-rose-50" : ""}`}
                      onClick={() => openRunDetail(r)}
                    >
                      <td className="py-2 pr-4 font-mono text-xs">{r.id.slice(0, 8)}…</td>
                      <td className="py-2 pr-4">
                        <span className={`px-1.5 py-0.5 text-xs rounded ${STATUS_BADGE[r.status] || ""}`}>{r.status}</span>
                      </td>
                      <td className="py-2 pr-4">{r.current_node_id || "-"}</td>
                      <td className="py-2 pr-4">{r.started_at ? new Date(r.started_at).toLocaleString() : "-"}</td>
                      <td className="py-2 text-red-600 text-xs">{r.error_message || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {expandedRunId && pendingApprovals.length > 0 && (
              <div className="mt-4 border-t pt-4 space-y-3">
                <h5 className="text-sm font-medium text-rose-800">待审批</h5>
                {pendingApprovals.filter((a) => a.status === "pending").map((a) => (
                  <div key={a.id} className="bg-rose-50 border border-rose-100 rounded p-3 text-sm">
                    <p className="font-medium">{a.title}</p>
                    <p className="text-gray-600 mt-1">{a.message}</p>
                    <div className="flex gap-2 mt-2">
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); decideApproval(expandedRunId, a.id, true); }}
                        className="bg-green-600 text-white px-3 py-1 rounded text-xs"
                      >
                        通过
                      </button>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); decideApproval(expandedRunId, a.id, false); }}
                        className="bg-red-600 text-white px-3 py-1 rounded text-xs"
                      >
                        拒绝
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {!isDraft && (
          <p className="text-sm text-amber-700 bg-amber-50 px-4 py-2 rounded border border-amber-100">
            已发布流程为只读。如需修改请复制为新草稿（后续版本支持）。
          </p>
        )}
      </div>
    </AppShell>
  );
}
