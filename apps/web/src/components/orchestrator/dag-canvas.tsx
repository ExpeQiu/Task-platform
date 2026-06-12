"use client";

import { DagEdge, DagNode, NodeType } from "@/lib/api";
import { useCallback, useRef, useState } from "react";

const NODE_W = 160;
const NODE_H = 64;

const NODE_STYLE: Record<NodeType, { border: string; badge: string; badgeColor: string }> = {
  start: { border: "border-indigo-500 border-2", badge: "Start", badgeColor: "text-gray-500" },
  agent: { border: "border-blue-300", badge: "Agent Task", badgeColor: "text-blue-500" },
  end: { border: "border-green-300", badge: "End", badgeColor: "text-green-500" },
  condition: { border: "border-amber-300", badge: "Condition", badgeColor: "text-amber-600" },
  parallel: { border: "border-purple-300", badge: "Parallel", badgeColor: "text-purple-500" },
  loop: { border: "border-orange-300", badge: "Loop", badgeColor: "text-orange-500" },
};

interface Props {
  nodes: DagNode[];
  edges: DagEdge[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onMoveNode: (id: string, x: number, y: number) => void;
}

export function DagCanvas({ nodes, edges, selectedId, onSelect, onMoveNode }: Props) {
  const dragRef = useRef<{ id: string; ox: number; oy: number } | null>(null);
  const movedRef = useRef(false);
  const [dragging, setDragging] = useState<string | null>(null);

  const nodeCenter = (n: DagNode) => ({
    cx: n.position.x + NODE_W / 2,
    cy: n.position.y + NODE_H / 2,
  });

  const onMouseDown = (e: React.MouseEvent, node: DagNode) => {
    e.stopPropagation();
    movedRef.current = false;
    dragRef.current = {
      id: node.id,
      ox: e.clientX - node.position.x,
      oy: e.clientY - node.position.y,
    };
    setDragging(node.id);
  };

  const onNodeClick = (e: React.MouseEvent, node: DagNode) => {
    e.stopPropagation();
    if (movedRef.current) return;
    onSelect(node.id);
  };

  const onMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragRef.current) return;
      movedRef.current = true;
      const { id, ox, oy } = dragRef.current;
      onMoveNode(id, Math.max(0, e.clientX - ox), Math.max(0, e.clientY - oy));
    },
    [onMoveNode]
  );

  const onMouseUp = () => {
    dragRef.current = null;
    setDragging(null);
  };

  const onCanvasClick = (e: React.MouseEvent) => {
    if (e.target !== e.currentTarget) return;
    onSelect(null);
  };

  return (
    <div
      className="relative flex-1 bg-gray-100 overflow-auto min-h-[420px] cursor-default"
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
      onClick={onCanvasClick}
    >
      <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ minWidth: 800, minHeight: 500 }}>
        {edges.map((edge) => {
          const src = nodes.find((n) => n.id === edge.source);
          const tgt = nodes.find((n) => n.id === edge.target);
          if (!src || !tgt) return null;
          const s = nodeCenter(src);
          const t = nodeCenter(tgt);
          return (
            <g key={edge.id}>
              <line x1={s.cx} y1={s.cy + NODE_H / 2} x2={t.cx} y2={t.cy - NODE_H / 2} stroke="#9ca3af" strokeWidth={2} markerEnd="url(#arrow)" />
            </g>
          );
        })}
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#9ca3af" />
          </marker>
        </defs>
      </svg>

      {nodes.map((node) => {
        const style = NODE_STYLE[node.type];
        const selected = selectedId === node.id;
        return (
          <div
            key={node.id}
            className={`absolute bg-white rounded-lg p-3 shadow-md w-40 text-center select-none cursor-pointer ${style.border} ${selected ? "ring-2 ring-indigo-400" : ""} ${dragging === node.id ? "opacity-80 z-10" : "z-0"}`}
            style={{ left: node.position.x, top: node.position.y, height: NODE_H }}
            onMouseDown={(e) => onMouseDown(e, node)}
            onClick={(e) => onNodeClick(e, node)}
          >
            <div className={`text-xs mb-0.5 ${style.badgeColor}`}>{style.badge}</div>
            <div className="font-semibold text-sm truncate">{node.label}</div>
          </div>
        );
      })}
    </div>
  );
}

export const DEFAULT_DAG: { nodes: DagNode[]; edges: DagEdge[] } = {
  nodes: [
    { id: "start", type: "start", label: "接收 Webhook", config: { trigger: "webhook" }, position: { x: 250, y: 40 } },
    { id: "openclaw", type: "agent", label: "OpenClaw 抓取", config: { objective: "抓取竞品数据" }, position: { x: 120, y: 180 } },
    { id: "hermes", type: "agent", label: "Hermes 总结", config: { objective: "生成分析报告" }, position: { x: 380, y: 180 } },
    { id: "end", type: "end", label: "输出报告并告警", config: { action: "notify" }, position: { x: 250, y: 320 } },
  ],
  edges: [
    { id: "e1", source: "start", target: "openclaw" },
    { id: "e2", source: "start", target: "hermes" },
    { id: "e3", source: "openclaw", target: "end" },
    { id: "e4", source: "hermes", target: "end" },
  ],
};

export const NODE_PALETTE: { type: NodeType; label: string; defaultLabel: string }[] = [
  { type: "start", label: "起点", defaultLabel: "触发入口" },
  { type: "agent", label: "Agent 任务", defaultLabel: "Agent 节点" },
  { type: "condition", label: "条件分支", defaultLabel: "条件判断" },
  { type: "parallel", label: "并行网关", defaultLabel: "并行分发" },
  { type: "loop", label: "循环", defaultLabel: "循环控制" },
  { type: "end", label: "终点", defaultLabel: "流程结束" },
];

export function newNodeId(type: NodeType, existing: DagNode[]): string {
  const base = type === "agent" ? "agent" : type;
  let i = existing.filter((n) => n.type === type).length + 1;
  let id = `${base}_${i}`;
  while (existing.some((n) => n.id === id)) {
    i += 1;
    id = `${base}_${i}`;
  }
  return id;
}

export function newEdgeId(edges: DagEdge[]): string {
  return `e${edges.length + 1}`;
}
