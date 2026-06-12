"use client";

import { AppShell } from "@/components/layout/app-shell";
import { useState } from "react";

const MOCK_MCPS = [
  { name: "RAG 知识库", type: "RAG", endpoint: "http://localhost:9001/mcp", status: "Connected" },
  { name: "Skill 插件", type: "Skill", endpoint: "http://localhost:9002/mcp", status: "Warning" },
  { name: "Mem0 记忆", type: "Memory", endpoint: "http://localhost:9003/mcp", status: "Error" },
];

const statusClass: Record<string, string> = {
  Connected: "bg-green-100 text-green-800",
  Warning: "bg-yellow-100 text-yellow-800",
  Error: "bg-red-100 text-red-800",
};

export default function McpPage() {
  const [toast, setToast] = useState("");

  const testConnection = (name: string) => {
    setToast(`${name} 连通性测试（Mock）：UI 占位，Phase 3 实现真实 MCP`);
    setTimeout(() => setToast(""), 3000);
  };

  return (
    <AppShell title="MCP 配置">
      {toast && <div className="mb-4 bg-gray-800 text-white px-4 py-3 rounded shadow text-sm">{toast}</div>}
      <p className="mb-4 text-sm text-gray-500">MVP 阶段为 UI 占位，真实 MCP 连通将在 Phase 3 实现。</p>
      <div className="bg-white shadow rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">类型</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Endpoint</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {MOCK_MCPS.map((mcp) => (
              <tr key={mcp.name}>
                <td className="px-6 py-4 text-sm font-medium">{mcp.name}</td>
                <td className="px-6 py-4 text-sm">{mcp.type}</td>
                <td className="px-6 py-4 text-sm font-mono text-gray-500">{mcp.endpoint}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs rounded-full ${statusClass[mcp.status]}`}>{mcp.status}</span>
                </td>
                <td className="px-6 py-4 text-right">
                  <button onClick={() => testConnection(mcp.name)} className="text-indigo-600 text-sm">测试连通性</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
