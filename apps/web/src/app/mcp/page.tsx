"use client";

import { AppShell } from "@/components/layout/app-shell";
import { McpHealth, McpServer, McpServerCreate, api } from "@/lib/api";
import { useCallback, useEffect, useState } from "react";

const DEFAULT_FORM: McpServerCreate = {
  name: "",
  mcp_type: "Custom",
  transport: "sse",
  endpoint: "",
  description: "",
  auth_config: {},
  extra_config: {},
  is_enabled: true,
};

const MCP_TYPES = ["RAG", "Skill", "Memory", "Custom"] as const;
const MCP_TRANSPORTS = ["sse", "http", "stdio"] as const;

const statusClass: Record<string, string> = {
  Connected: "bg-green-100 text-green-800",
  Warning: "bg-yellow-100 text-yellow-800",
  Error: "bg-red-100 text-red-800",
  Disabled: "bg-gray-100 text-gray-600",
};

const inputClass =
  "w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500";

function FieldLabel({ children, hint }: { children: React.ReactNode; hint?: string }) {
  return (
    <label className="block text-sm font-medium text-gray-700 mb-1">
      {children}
      {hint && <span className="ml-1 text-xs font-normal text-gray-400">{hint}</span>}
    </label>
  );
}

function parseJsonObject(raw: string): Record<string, string> | null {
  if (!raw.trim()) return {};
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return null;
    return parsed as Record<string, string>;
  } catch {
    return null;
  }
}

export default function McpPage() {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<McpServer | null>(null);
  const [form, setForm] = useState<McpServerCreate>({ ...DEFAULT_FORM });
  const [authJson, setAuthJson] = useState("{}");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [healthMap, setHealthMap] = useState<Record<string, McpHealth>>({});
  const [probingId, setProbingId] = useState<string | null>(null);

  const load = useCallback(() => {
    api.listMcpServers().then(setServers).catch((e) => setMessage(String(e)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = () => {
    setForm({ ...DEFAULT_FORM });
    setAuthJson("{}");
    setEditing(null);
  };

  const openCreate = () => {
    resetForm();
    setShowForm(true);
    setMessage("");
  };

  const openEdit = (server: McpServer) => {
    setEditing(server);
    setForm({
      name: server.name,
      mcp_type: server.mcp_type,
      transport: server.transport as McpServerCreate["transport"],
      endpoint: server.endpoint,
      description: server.description,
      is_enabled: server.is_enabled,
    });
    setAuthJson(JSON.stringify(server.auth_config || {}, null, 2));
    setShowForm(true);
    setMessage("");
  };

  const validateForm = (): string | null => {
    if (!form.name.trim()) return "请填写 MCP 名称";
    if (!form.endpoint.trim()) return "请填写 Endpoint";
    if (parseJsonObject(authJson) === null) return "鉴权配置 JSON 格式无效";
    return null;
  };

  const saveServer = async () => {
    const err = validateForm();
    if (err) {
      setMessage(err);
      return;
    }
    setSubmitting(true);
    setMessage("");
    const payload: McpServerCreate = {
      ...form,
      name: form.name.trim(),
      endpoint: form.endpoint.trim(),
      auth_config: parseJsonObject(authJson) || {},
    };
    try {
      if (editing) {
        await api.updateMcpServer(editing.id, payload);
      } else {
        await api.createMcpServer(payload);
      }
      setShowForm(false);
      resetForm();
      load();
    } catch (e) {
      setMessage(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  const probeConnection = async (server: McpServer) => {
    setProbingId(server.id);
    try {
      const health = await api.probeMcpServer(server.id);
      setHealthMap((prev) => ({ ...prev, [server.id]: health }));
    } catch (e) {
      setMessage(String(e));
    } finally {
      setProbingId(null);
    }
  };

  const toggleEnabled = async (server: McpServer) => {
    try {
      await api.updateMcpServer(server.id, { is_enabled: !server.is_enabled });
      load();
    } catch (e) {
      setMessage(String(e));
    }
  };

  const deleteServer = async (server: McpServer) => {
    if (!confirm(`确认删除 MCP「${server.name}」？`)) return;
    try {
      await api.deleteMcpServer(server.id);
      load();
    } catch (e) {
      setMessage(String(e));
    }
  };

  const displayStatus = (server: McpServer) => {
    if (!server.is_enabled) return "Disabled";
    return healthMap[server.id]?.status ?? "—";
  };

  return (
    <AppShell title="MCP 配置">
      <div className="mb-6 bg-indigo-50 border border-indigo-100 rounded-lg p-5">
        <h3 className="text-sm font-semibold text-indigo-900 mb-2">Model Context Protocol</h3>
        <p className="text-sm text-indigo-800">
          接入 RAG 知识库、Skill 插件、Memory 记忆等 MCP 扩展，为 Agent 提供统一工具调用能力。
          支持 SSE / HTTP 远程传输，连通性测试将发送 MCP <code className="text-xs bg-white px-1 rounded">initialize</code> 握手。
        </p>
      </div>

      <div className="flex justify-between items-center mb-4">
        <p className="text-sm text-gray-500">共 {servers.length} 个 MCP 组件</p>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700"
        >
          新增 MCP
        </button>
      </div>

      {message && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">{message}</div>
      )}

      <div className="bg-white shadow rounded-lg border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">类型</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">传输</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Endpoint</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {servers.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-sm text-gray-400">
                  暂无 MCP 配置，{" "}
                  <button onClick={openCreate} className="text-indigo-600 hover:text-indigo-800">
                    新增第一个
                  </button>
                </td>
              </tr>
            )}
            {servers.map((server) => {
              const status = displayStatus(server);
              const health = healthMap[server.id];
              return (
                <tr key={server.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium">{server.name}</div>
                    {server.description && (
                      <div className="text-xs text-gray-500 mt-0.5">{server.description}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm">{server.mcp_type}</td>
                  <td className="px-6 py-4 text-sm uppercase">{server.transport}</td>
                  <td className="px-6 py-4 text-sm font-mono text-gray-500 max-w-xs truncate" title={server.endpoint}>
                    {server.endpoint}
                  </td>
                  <td className="px-6 py-4">
                    {status === "—" ? (
                      <span className="text-xs text-gray-400">未检测</span>
                    ) : (
                      <span className={`px-2 py-1 text-xs rounded-full ${statusClass[status] || "bg-gray-100"}`}>
                        {status}
                      </span>
                    )}
                    {health && (
                      <div className="text-xs text-gray-500 mt-1">
                        {health.latency_ms != null && `${health.latency_ms}ms`}
                        {health.tool_count != null && ` · ${health.tool_count} tools`}
                        {health.error && <span className="text-red-500"> · {health.error}</span>}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right space-x-3 text-sm">
                    <button
                      onClick={() => probeConnection(server)}
                      disabled={probingId === server.id}
                      className="text-indigo-600 hover:text-indigo-900 disabled:opacity-50"
                    >
                      {probingId === server.id ? "测试中…" : "测试连通性"}
                    </button>
                    <button onClick={() => openEdit(server)} className="text-gray-600 hover:text-gray-900">
                      编辑
                    </button>
                    <button onClick={() => toggleEnabled(server)} className="text-gray-600 hover:text-gray-900">
                      {server.is_enabled ? "停用" : "启用"}
                    </button>
                    <button onClick={() => deleteServer(server)} className="text-red-500 hover:text-red-700">
                      删除
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
            <h3 className="text-lg font-bold mb-4">{editing ? "编辑 MCP" : "新增 MCP"}</h3>
            <div className="space-y-4">
              <div>
                <FieldLabel>名称</FieldLabel>
                <input
                  className={inputClass}
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="如 公司 Wiki RAG"
                />
              </div>
              <div>
                <FieldLabel>类型</FieldLabel>
                <select
                  className={inputClass}
                  value={form.mcp_type}
                  onChange={(e) => setForm({ ...form, mcp_type: e.target.value })}
                >
                  {MCP_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <FieldLabel hint="sse/http 可远程探测，stdio 仅本地">传输协议</FieldLabel>
                <select
                  className={inputClass}
                  value={form.transport}
                  onChange={(e) =>
                    setForm({ ...form, transport: e.target.value as McpServerCreate["transport"] })
                  }
                >
                  {MCP_TRANSPORTS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <FieldLabel hint="MCP Server JSON-RPC 地址">Endpoint</FieldLabel>
                <input
                  className={inputClass}
                  value={form.endpoint}
                  onChange={(e) => setForm({ ...form, endpoint: e.target.value })}
                  placeholder="http://localhost:9001/mcp"
                />
              </div>
              <div>
                <FieldLabel>描述</FieldLabel>
                <textarea
                  className={inputClass}
                  rows={2}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
              <div>
                <FieldLabel hint='如 {"bearer_token":"..."} 或 {"api_key":"..."}'>
                  鉴权配置 (JSON)
                </FieldLabel>
                <textarea
                  className={`${inputClass} font-mono text-xs`}
                  rows={3}
                  value={authJson}
                  onChange={(e) => setAuthJson(e.target.value)}
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_enabled}
                  onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })}
                />
                创建后立即启用
              </label>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setShowForm(false);
                  resetForm();
                }}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
              >
                取消
              </button>
              <button
                onClick={saveServer}
                disabled={submitting}
                className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 disabled:opacity-50"
              >
                {submitting ? "保存中…" : "保存"}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
