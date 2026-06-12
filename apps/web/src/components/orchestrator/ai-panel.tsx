"use client";

import { Adapter, api, AiChatMessage, AiOrchestratorResponse, WorkflowDag } from "@/lib/api";
import { useEffect, useRef, useState } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
  adapters: Adapter[];
  currentDag: WorkflowDag;
  onApply: (dag: WorkflowDag, workflowName?: string) => void;
}

const QUICK_PROMPTS = [
  "抓取竞品数据并生成分析报告",
  "Webhook 触发，并行 OpenClaw 抓取和 Hermes 总结",
  "抓取后条件判断，失败则循环重试",
];

function AiBadge() {
  return (
    <span className="inline-flex items-center px-1 py-0.5 rounded text-[10px] font-semibold bg-white/20 text-white leading-none">
      AI
    </span>
  );
}

export function AiOrchestratorButton({ onClick, disabled }: { onClick: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white px-3 py-1.5 rounded-md text-sm hover:from-violet-700 hover:to-indigo-700 disabled:opacity-50"
      title="AI 智能编排"
    >
      <AiBadge />
      <span>AI 编排</span>
    </button>
  );
}

export function AiOrchestratorPanel({ open, onClose, adapters, currentDag, onApply }: Props) {
  const [messages, setMessages] = useState<AiChatMessage[]>([
    {
      role: "assistant",
      content: "你好，我是流程编排助手。描述你的业务需求，我会自动生成 DAG 流程图并应用到画布。",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState<AiOrchestratorResponse | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  const send = async (text: string) => {
    const msg = text.trim();
    if (!msg || loading) return;
    setInput("");
    const userMsg: AiChatMessage = { role: "user", content: msg };
    const nextHistory = [...messages, userMsg];
    setMessages(nextHistory);
    setLoading(true);
    setPending(null);

    try {
      const resp = await api.aiOrchestratorChat({
        message: msg,
        history: messages.filter((m) => m.role === "user" || m.role === "assistant"),
        current_dag: currentDag,
        adapter_names: adapters.map((a) => a.name),
      });
      setMessages([...nextHistory, { role: "assistant", content: resp.reply }]);
      if (resp.dag) setPending(resp);
    } catch (e) {
      setMessages([
        ...nextHistory,
        { role: "assistant", content: e instanceof Error ? e.message : "请求失败，请稍后重试" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const applyPending = () => {
    if (!pending?.dag) return;
    onApply(pending.dag, pending.workflow_name || undefined);
    setPending(null);
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "✓ 流程已应用到画布，您可以继续微调节点或保存草稿。" },
    ]);
  };

  if (!open) return null;

  return (
    <div className="absolute right-0 top-0 bottom-0 w-[360px] z-30 flex flex-col bg-white border-l border-gray-200 shadow-xl">
      <div className="px-4 py-3 border-b bg-gradient-to-r from-violet-50 to-indigo-50 flex justify-between items-center shrink-0">
        <div className="flex items-center gap-2">
          <AiBadge />
          <span className="font-medium text-gray-800 text-sm">AI 流程编排</span>
        </div>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg leading-none" title="关闭">
          ×
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[90%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-800 border border-gray-200"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-3 py-2 text-sm text-gray-500 animate-pulse">正在生成流程…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {pending?.dag && (
        <div className="px-3 py-2 border-t bg-green-50 shrink-0">
          <p className="text-xs text-green-800 mb-2">
            已生成 {pending.dag.nodes.length} 个节点 · {pending.dag.edges.length} 条连线
          </p>
          <button
            type="button"
            onClick={applyPending}
            className="w-full py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700"
          >
            应用到画布
          </button>
        </div>
      )}

      <div className="p-3 border-t shrink-0 space-y-2">
        <div className="flex flex-wrap gap-1">
          {QUICK_PROMPTS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => send(p)}
              disabled={loading}
              className="text-xs px-2 py-1 rounded-full bg-violet-50 text-violet-700 border border-violet-100 hover:bg-violet-100 disabled:opacity-50"
            >
              {p.length > 14 ? p.slice(0, 14) + "…" : p}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="描述你想要的流程…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send(input)}
            disabled={loading}
          />
          <button
            type="button"
            onClick={() => send(input)}
            disabled={loading || !input.trim()}
            className="px-3 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
