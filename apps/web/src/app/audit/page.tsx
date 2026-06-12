"use client";

import { AppShell } from "@/components/layout/app-shell";
import { api, AuditEvent } from "@/lib/api";
import { useEffect, useState } from "react";

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.listAudit().then(setEvents).catch(console.error);
  }, []);

  const filtered = events.filter(
    (e) => !search || e.target.includes(search) || e.detail.includes(search) || e.action.includes(search)
  );

  return (
    <AppShell title="治理与审计">
      <div className="flex justify-between items-center mb-6">
        <input
          type="text"
          placeholder="检索操作对象..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border rounded-md text-sm py-2 px-4 border-gray-300"
        />
        <a
          href={api.exportAudit()}
          className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md text-sm hover:bg-gray-50"
        >
          导出 CSV
        </a>
      </div>
      <div className="bg-white shadow rounded-lg border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">时间</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作人</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">动作</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">对象</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">详情</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filtered.map((e) => (
              <tr key={e.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm text-gray-500">{new Date(e.created_at).toLocaleString()}</td>
                <td className="px-6 py-4 text-sm">{e.actor}</td>
                <td className="px-6 py-4 text-sm font-mono text-indigo-600">{e.action}</td>
                <td className="px-6 py-4 text-sm font-mono">{e.target.slice(0, 12)}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{e.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
