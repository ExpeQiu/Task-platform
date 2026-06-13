"use client";

import { AppShell } from "@/components/layout/app-shell";
import { api, Alert } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";

const severityClass: Record<string, string> = {
  Critical: "bg-red-100 text-red-800",
  Warning: "bg-yellow-100 text-yellow-800",
  Info: "bg-blue-100 text-blue-800",
};

const ALERT_TYPES = [
  { value: "", label: "全部类型" },
  { value: "NoProgressDetected", label: "无进展" },
  { value: "BudgetExceeded", label: "预算超限" },
  { value: "LoopLimitExceeded", label: "循环上限" },
  { value: "AgentTimeout", label: "Agent 超时" },
  { value: "TaskFailed", label: "任务失败" },
];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [typeFilter, setTypeFilter] = useState("");

  const load = () => {
    api.listAlerts(typeFilter ? { alert_type: typeFilter } : undefined).then(setAlerts).catch(console.error);
  };

  useEffect(() => { load(); }, [typeFilter]);

  const resolve = async (id: string, status: string) => {
    await api.updateAlert(id, status);
    load();
  };

  return (
    <AppShell title="告警中心">
      <div className="bg-white shadow rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b flex justify-between items-center bg-gray-50">
          <h3 className="text-lg font-medium">活跃告警</h3>
          <div className="flex items-center gap-3">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="border rounded-md text-sm py-1.5 px-3 border-gray-300"
            >
              {ALERT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
              {alerts.length} 条未处理
            </span>
          </div>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">级别</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">类型</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">内容</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">关联 Run</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">时间</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {alerts.map((alert) => (
              <tr key={alert.id}>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${severityClass[alert.severity] || ""}`}>
                    {alert.severity}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm">{alert.alert_type}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{alert.content}</td>
                <td className="px-6 py-4 text-sm">
                  {alert.run_id ? (
                    <Link href={`/runs/${alert.run_id}`} className="text-indigo-600 hover:underline font-mono text-xs">
                      {alert.run_id.slice(0, 8)}…
                    </Link>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">{new Date(alert.created_at).toLocaleString()}</td>
                <td className="px-6 py-4 text-right space-x-2 text-sm">
                  <button onClick={() => resolve(alert.id, "ack")} className="text-indigo-600">确认</button>
                  <button onClick={() => resolve(alert.id, "resolved")} className="text-green-600">解决</button>
                </td>
              </tr>
            ))}
            {alerts.length === 0 && (
              <tr><td colSpan={6} className="px-6 py-8 text-center text-gray-500">暂无活跃告警</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
