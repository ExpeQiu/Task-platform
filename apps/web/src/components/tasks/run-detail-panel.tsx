"use client";

import Link from "next/link";
import { RunTimeline } from "@/lib/api";

const statusClass: Record<string, string> = {
  Running: "bg-blue-100 text-blue-800",
  Success: "bg-green-100 text-green-800",
  Failed: "bg-red-100 text-red-800",
  Terminated: "bg-orange-100 text-orange-800",
  Iterating: "bg-purple-100 text-purple-800",
  Reviewing: "bg-yellow-100 text-yellow-800",
};

const verificationLabel: Record<string, string> = {
  rule_based: "规则",
  llm_agent: "LLM",
  hybrid: "混合",
};

interface Props {
  timeline: RunTimeline;
  logs?: string[];
  taskId?: string;
  compact?: boolean;
}

export function RunDetailPanel({ timeline, logs = [], taskId, compact }: Props) {
  const tokens = Number(timeline.budget_usage?.tokens ?? 0);
  const budgetLimit = timeline.budget_limit;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h4 className="font-medium">运行详情</h4>
          <p className="text-sm text-gray-600 mt-1 font-mono">{timeline.run_id}</p>
          <p className="text-sm text-gray-600 mt-1">目标: {timeline.objective}</p>
          {taskId && (
            <Link href={`/tasks`} className="text-xs text-indigo-600 hover:underline mt-1 inline-block">
              任务 {taskId.slice(0, 8)}…
            </Link>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${statusClass[timeline.status] || "bg-gray-100"}`}>
            {timeline.status}
          </span>
          <span className="text-xs text-gray-500">
            验证: {verificationLabel[timeline.verification_mode] || timeline.verification_mode}
          </span>
        </div>
      </div>

      {timeline.termination_reason && (
        <div className="bg-amber-50 border border-amber-200 text-amber-900 px-3 py-2 rounded text-sm">
          终止原因: {timeline.termination_reason}
        </div>
      )}

      <div className={`grid gap-3 text-sm ${compact ? "grid-cols-2" : "grid-cols-2 md:grid-cols-4"}`}>
        <div className="bg-gray-50 p-2 rounded">
          <div className="text-gray-500 text-xs">轮次</div>
          <div className="font-medium">{timeline.iteration_count} / {timeline.max_iterations}</div>
        </div>
        <div className="bg-gray-50 p-2 rounded">
          <div className="text-gray-500 text-xs">Token 消耗</div>
          <div className="font-medium">
            {tokens}
            {budgetLimit ? ` / ${budgetLimit}` : ""}
          </div>
        </div>
        {!compact && (
          <div className="bg-gray-50 p-2 rounded col-span-2">
            <div className="text-gray-500 text-xs">完成标准</div>
            <div className="font-mono text-xs truncate">
              {timeline.success_criteria?.rules?.length
                ? JSON.stringify(timeline.success_criteria)
                : "未配置"}
            </div>
          </div>
        )}
      </div>

      {timeline.long_term_memory && timeline.long_term_memory.length > 0 && (
        <div>
          <h5 className="text-sm font-medium text-gray-700 mb-2">注入记忆 ({timeline.long_term_memory.length})</h5>
          <div className="space-y-1 max-h-32 overflow-auto">
            {timeline.long_term_memory.map((m, i) => (
              <div key={i} className="text-xs bg-indigo-50 p-2 rounded border border-indigo-100">
                <span className="font-medium">{m.key as string}</span>
                <span className="text-gray-500 ml-2">[{m.scope as string}]</span>
                <p className="text-gray-600 mt-0.5 truncate">{m.content as string}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {timeline.iterations.length > 0 && (
        <div>
          <h5 className="text-sm font-medium text-gray-700 mb-2">迭代记录</h5>
          <div className="space-y-2">
            {timeline.iterations.map((it) => (
              <div key={it.iteration} className="border rounded p-3 text-sm">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-medium">第 {it.iteration} 轮</span>
                  <span className="text-gray-500">Agent: {it.agent_status}</span>
                </div>
                {it.verification && (
                  <div
                    className={`text-xs mt-1 ${
                      it.verification.verdict === "passed"
                        ? "text-green-700"
                        : it.verification.verdict === "needs_continue"
                          ? "text-blue-700"
                          : "text-red-700"
                    }`}
                  >
                    平台验证: {it.verification.verdict} — {it.verification.reason}
                    {it.verification.verified_by?.includes("llm") && (
                      <span className="ml-1 text-purple-600">[LLM]</span>
                    )}
                  </div>
                )}
                {!compact && (
                  <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-auto max-h-24">
                    {JSON.stringify(it.result_payload, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {logs.length > 0 && (
        <div>
          <h5 className="text-sm font-medium text-gray-700 mb-2">事件时间线</h5>
          <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto max-h-48">{logs.join("\n")}</pre>
        </div>
      )}
    </div>
  );
}
