"use client";

import { AppShell } from "@/components/layout/app-shell";
import { api, PendingApproval } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function ApprovalsPage() {
  const [items, setItems] = useState<PendingApproval[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  const load = () => api.listPendingApprovals().then(setItems).catch(console.error);
  useEffect(() => { load(); }, []);

  const decide = async (item: PendingApproval, approved: boolean) => {
    try {
      await api.decideApproval(item.workflow_run_id, item.id, {
        approved,
        note: notes[item.id] || "",
      });
      setMessage(approved ? "已通过审批" : "已拒绝审批");
      load();
    } catch (e) {
      setMessage(String(e));
    }
  };

  return (
    <AppShell title="审批收件箱">
      {message && <div className="mb-4 bg-indigo-50 text-indigo-800 px-4 py-2 rounded text-sm">{message}</div>}
      <p className="text-sm text-gray-600 mb-6">
        待处理工作流人工审批节点。也可在
        <Link href="/orchestrator" className="text-indigo-600 mx-1 hover:underline">流程编排</Link>
        查看运行记录。
      </p>

      <div className="space-y-4">
        {items.map((item) => (
          <div key={item.id} className="bg-white border rounded-lg p-5 shadow-sm">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-medium">{item.title || "人工审批"}</h3>
                <p className="text-sm text-gray-600 mt-1">{item.message}</p>
                <p className="text-xs text-gray-400 mt-2">
                  流程: {item.workflow_name} · 节点: {item.node_id} · Run: {item.workflow_run_id.slice(0, 8)}…
                </p>
                <span className="inline-block mt-1 text-xs px-2 py-0.5 bg-rose-100 text-rose-800 rounded">
                  {item.run_status}
                </span>
              </div>
              <span className="text-xs text-gray-400">{new Date(item.created_at).toLocaleString()}</span>
            </div>
            <textarea
              className="w-full mt-3 border rounded-md px-3 py-2 text-sm"
              rows={2}
              placeholder="审批备注（可选）"
              value={notes[item.id] || ""}
              onChange={(e) => setNotes({ ...notes, [item.id]: e.target.value })}
            />
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => decide(item, true)}
                className="bg-green-600 text-white px-4 py-1.5 rounded text-sm hover:bg-green-700"
              >
                通过
              </button>
              <button
                onClick={() => decide(item, false)}
                className="bg-red-600 text-white px-4 py-1.5 rounded text-sm hover:bg-red-700"
              >
                拒绝
              </button>
            </div>
          </div>
        ))}
        {items.length === 0 && (
          <div className="bg-white border rounded-lg p-12 text-center text-gray-500">
            暂无待审批事项
          </div>
        )}
      </div>
    </AppShell>
  );
}
