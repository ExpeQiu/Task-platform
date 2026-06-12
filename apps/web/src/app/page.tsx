"use client";

import { AppShell } from "@/components/layout/app-shell";
import { api, DashboardMetrics } from "@/lib/api";
import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

const COLORS = ["#6366f1", "#8b5cf6", "#06b6d4", "#10b981"];

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);

  useEffect(() => {
    api.getDashboard().then(setMetrics).catch(console.error);
  }, []);

  if (!metrics) {
    return (
      <AppShell title="数据看板 BI">
        <p className="text-gray-500">加载中...</p>
      </AppShell>
    );
  }

  const trend = metrics.trend ?? [];
  const agentDistribution = metrics.agent_distribution ?? [];
  const adapterStats = metrics.adapter_stats ?? [];

  const cards = [
    { label: "总任务数", value: metrics.total_tasks, color: "text-gray-900" },
    { label: "活跃运行中", value: metrics.active_runs, pulse: true },
    { label: "成功率", value: `${metrics.success_rate}%`, color: "text-gray-900" },
    { label: "队列积压", value: metrics.queue_backlog, color: "text-red-600", suffix: "条待调度" },
  ];

  return (
    <AppShell title="数据看板 BI">
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {cards.map((card) => (
            <div key={card.label} className="bg-white rounded-lg shadow p-6 border border-gray-100">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-gray-500 text-sm font-medium">{card.label}</h3>
                {card.pulse && <div className="w-3 h-3 bg-blue-500 rounded-full pulse-dot" />}
              </div>
              <div className="flex items-baseline">
                <span className={`text-3xl font-bold ${card.color || ""}`}>{card.value}</span>
                {card.suffix && <span className="ml-2 text-sm text-gray-500">{card.suffix}</span>}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6 border border-gray-100">
            <h3 className="text-lg font-medium text-gray-900 mb-4">任务执行趋势</h3>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trend.slice(0, 12)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="success" stroke="#6366f1" name="成功" />
                <Line type="monotone" dataKey="failed" stroke="#ef4444" name="失败" />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-white rounded-lg shadow p-6 border border-gray-100">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Agent 任务负载分布</h3>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={agentDistribution}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label
                >
                  {agentDistribution.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {adapterStats.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 border border-gray-100">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Adapter 运行指标</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="pb-2 pr-4">名称</th>
                    <th className="pb-2 pr-4">类型</th>
                    <th className="pb-2 pr-4">协议</th>
                    <th className="pb-2 pr-4">状态</th>
                    <th className="pb-2 pr-4 text-right">分配数</th>
                    <th className="pb-2 pr-4 text-right">成功率</th>
                    <th className="pb-2 text-right">平均延迟</th>
                  </tr>
                </thead>
                <tbody>
                  {adapterStats.map((a) => (
                    <tr key={a.adapter_id} className="border-b border-gray-50">
                      <td className="py-2 pr-4 font-medium">{a.name}</td>
                      <td className="py-2 pr-4 text-gray-600">{a.adapter_type}</td>
                      <td className="py-2 pr-4 text-gray-600">{a.protocol === "push" ? "Push" : "Pull"}</td>
                      <td className="py-2 pr-4">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${a.is_online ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}`}>
                          {a.is_online ? "Online" : "Offline"}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-right">{a.total_assignments}</td>
                      <td className="py-2 pr-4 text-right">
                        {a.success_count + a.failed_count > 0 ? `${a.success_rate}%` : "—"}
                      </td>
                      <td className="py-2 text-right">
                        {a.avg_latency_ms != null ? `${a.avg_latency_ms} ms` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
