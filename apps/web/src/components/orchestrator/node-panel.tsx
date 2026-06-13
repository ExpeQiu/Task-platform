"use client";

import { Adapter, DagEdge, DagNode, NodeType } from "@/lib/api";

interface Props {
  node: DagNode | null;
  nodes: DagNode[];
  edges: DagEdge[];
  adapters: Adapter[];
  onChange: (node: DagNode) => void;
  onDelete: (id: string) => void;
  onAddEdge: (source: string, target: string) => void;
  onRemoveEdge: (edgeId: string) => void;
  onClose?: () => void;
}

const inputClass = "w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm";

export function NodePanel({ node, nodes, edges, adapters, onChange, onDelete, onAddEdge, onRemoveEdge, onClose }: Props) {
  if (!node) {
    return (
      <div className="w-64 shrink-0 border-l bg-gray-50 p-4 text-sm text-gray-500 flex flex-col">
        <div className="flex justify-between items-center mb-2">
          <span className="font-medium text-gray-600">节点属性</span>
          {onClose && (
            <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none" title="收起">
              ×
            </button>
          )}
        </div>
        点击画布上的节点进行编辑，或从左侧面板添加新节点。
      </div>
    );
  }

  const outgoing = edges.filter((e) => e.source === node.id);
  const incoming = edges.filter((e) => e.target === node.id);
  const otherNodes = nodes.filter((n) => n.id !== node.id);

  const patch = (partial: Partial<DagNode>) => onChange({ ...node, ...partial });
  const patchConfig = (key: string, value: string | number | undefined) =>
    onChange({ ...node, config: { ...node.config, [key]: value } });

  return (
    <div className="w-64 shrink-0 border-l bg-white p-4 overflow-y-auto text-sm space-y-3">
      <div className="flex justify-between items-center">
        <h4 className="font-medium text-gray-800">节点属性</h4>
        <div className="flex items-center gap-2">
          {node.type !== "start" && (
            <button type="button" onClick={() => onDelete(node.id)} className="text-red-500 text-xs hover:underline">
              删除
            </button>
          )}
          {onClose && (
            <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none" title="收起">
              ×
            </button>
          )}
        </div>
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">ID</label>
        <input className={inputClass + " bg-gray-50"} value={node.id} readOnly />
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">类型</label>
        <input className={inputClass + " bg-gray-50"} value={node.type} readOnly />
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">标签</label>
        <input className={inputClass} value={node.label} onChange={(e) => patch({ label: e.target.value })} />
      </div>

      {node.type === "start" && (
        <div>
          <label className="block text-xs text-gray-500 mb-1">触发方式</label>
          <select className={inputClass} value={node.config.trigger || "webhook"} onChange={(e) => patchConfig("trigger", e.target.value)}>
            <option value="webhook">Webhook</option>
            <option value="cron">定时 Cron</option>
            <option value="manual">手动触发</option>
          </select>
        </div>
      )}

      {node.type === "agent" && (
        <>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Agent 适配器</label>
            <select
              className={inputClass}
              value={node.config.adapter_id || ""}
              onChange={(e) => patchConfig("adapter_id", e.target.value || undefined)}
            >
              <option value="">请选择</option>
              {adapters.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} {a.is_online ? "" : "(离线)"}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">任务目标</label>
            <textarea
              className={inputClass + " h-16 resize-none"}
              value={node.config.objective || ""}
              onChange={(e) => patchConfig("objective", e.target.value)}
            />
          </div>
        </>
      )}

      {node.type === "condition" && (
        <div>
          <label className="block text-xs text-gray-500 mb-1">条件表达式</label>
          <input
            className={inputClass}
            placeholder="context.status == 'ok'"
            value={node.config.expression || ""}
            onChange={(e) => patchConfig("expression", e.target.value)}
          />
          <p className="text-xs text-gray-400 mt-1">true 走第一条出边，false 走第二条</p>
        </div>
      )}

      {node.type === "loop" && (
        <div>
          <label className="block text-xs text-gray-500 mb-1">最大循环次数</label>
          <input
            type="number"
            className={inputClass}
            min={1}
            value={node.config.max_iterations ?? 3}
            onChange={(e) => patchConfig("max_iterations", parseInt(e.target.value, 10))}
          />
        </div>
      )}

      {node.type === "approval" && (
        <>
          <div>
            <label className="block text-xs text-gray-500 mb-1">审批标题</label>
            <input
              className={inputClass}
              value={node.config.title || ""}
              onChange={(e) => patchConfig("title", e.target.value)}
              placeholder="例如：发布前人工确认"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">审批说明</label>
            <textarea
              className={inputClass + " h-20 resize-none"}
              value={node.config.message || ""}
              onChange={(e) => patchConfig("message", e.target.value)}
              placeholder="描述审批人需要确认的内容"
            />
          </div>
        </>
      )}

      {node.type === "end" && (
        <div>
          <label className="block text-xs text-gray-500 mb-1">结束动作</label>
          <select className={inputClass} value={node.config.action || "notify"} onChange={(e) => patchConfig("action", e.target.value)}>
            <option value="notify">发送告警通知</option>
            <option value="report">输出报告</option>
            <option value="none">无</option>
          </select>
        </div>
      )}

      <div className="pt-2 border-t">
        <div className="text-xs text-gray-500 mb-1">入边 ({incoming.length})</div>
        {incoming.map((e) => (
          <div key={e.id} className="flex justify-between text-xs py-0.5">
            <span className="truncate">{e.source} → {node.id}</span>
            <button type="button" className="text-red-400 ml-1" onClick={() => onRemoveEdge(e.id)}>×</button>
          </div>
        ))}
      </div>

      <div>
        <div className="text-xs text-gray-500 mb-1">出边 ({outgoing.length})</div>
        {outgoing.map((e) => (
          <div key={e.id} className="flex justify-between text-xs py-0.5">
            <span className="truncate">{node.id} → {e.target}</span>
            <button type="button" className="text-red-400 ml-1" onClick={() => onRemoveEdge(e.id)}>×</button>
          </div>
        ))}
        {otherNodes.length > 0 && (
          <div className="flex gap-1 mt-1">
            <select id="edge-target" className={inputClass + " flex-1"} defaultValue="">
              <option value="">添加出边到…</option>
              {otherNodes.map((n) => (
                <option key={n.id} value={n.id}>{n.label} ({n.id})</option>
              ))}
            </select>
            <button
              type="button"
              className="px-2 py-1 bg-indigo-600 text-white rounded text-xs"
              onClick={() => {
                const sel = document.getElementById("edge-target") as HTMLSelectElement;
                if (sel?.value) {
                  onAddEdge(node.id, sel.value);
                  sel.value = "";
                }
              }}
            >
              +
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export function PaletteItem({
  type,
  label,
  onAdd,
}: {
  type: NodeType;
  label: string;
  onAdd: (type: NodeType) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onAdd(type)}
      className="w-full text-left px-3 py-2 text-sm border border-gray-200 rounded-md hover:bg-indigo-50 hover:border-indigo-200"
    >
      + {label}
    </button>
  );
}
