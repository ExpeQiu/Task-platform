"use client";

import { AppShell } from "@/components/layout/app-shell";
import { Adapter, AdapterCreate, AdapterHealth, api } from "@/lib/api";
import { useCallback, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const DEFAULT_FORM: AdapterCreate = {
  name: "",
  adapter_type: "generic",
  protocol: "push",
  endpoint: "",
  description: "",
  auth_config: {},
  status_mapping: {},
  is_online: true,
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

export default function AdaptersPage() {
  const [adapters, setAdapters] = useState<Adapter[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Adapter | null>(null);
  const [form, setForm] = useState<AdapterCreate>({ ...DEFAULT_FORM });
  const [authJson, setAuthJson] = useState("{}");
  const [mappingJson, setMappingJson] = useState("{}");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [healthMap, setHealthMap] = useState<Record<string, AdapterHealth>>({});
  const [checkingId, setCheckingId] = useState<string | null>(null);

  const load = useCallback(() => {
    api.listAdapters().then(setAdapters).catch((e) => setMessage(String(e)));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const resetForm = () => {
    setForm({ ...DEFAULT_FORM });
    setAuthJson("{}");
    setMappingJson("{}");
    setEditing(null);
  };

  const openCreate = () => {
    resetForm();
    setShowForm(true);
    setMessage("");
  };

  const openEdit = (adapter: Adapter) => {
    setEditing(adapter);
    setForm({
      name: adapter.name,
      adapter_type: adapter.adapter_type,
      protocol: adapter.protocol as "push" | "pull",
      endpoint: adapter.endpoint,
      description: adapter.description,
      is_online: adapter.is_online,
    });
    setAuthJson(JSON.stringify(adapter.auth_config || {}, null, 2));
    setMappingJson(JSON.stringify(adapter.status_mapping || {}, null, 2));
    setShowForm(true);
    setMessage("");
  };

  const validateForm = (): string | null => {
    if (!form.name.trim()) return "请填写适配器名称";
    if (!form.endpoint.trim()) return "请填写 Endpoint";
    if (parseJsonObject(authJson) === null) return "鉴权配置 JSON 格式无效";
    if (parseJsonObject(mappingJson) === null) return "状态映射 JSON 格式无效";
    return null;
  };

  const saveAdapter = async () => {
    const err = validateForm();
    if (err) {
      setMessage(err);
      return;
    }
    setSubmitting(true);
    setMessage("");
    const payload: AdapterCreate = {
      ...form,
      name: form.name.trim(),
      endpoint: form.endpoint.trim(),
      auth_config: parseJsonObject(authJson) || {},
      status_mapping: parseJsonObject(mappingJson) || {},
    };
    try {
      if (editing) {
        await api.updateAdapter(editing.id, payload);
      } else {
        await api.createAdapter(payload);
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

  const toggleOnline = async (adapter: Adapter) => {
    try {
      await api.updateAdapter(adapter.id, { is_online: !adapter.is_online });
      load();
    } catch (e) {
      setMessage(String(e));
    }
  };

  const checkHealth = async (adapter: Adapter) => {
    setCheckingId(adapter.id);
    try {
      const health = await api.checkAdapterHealth(adapter.id);
      setHealthMap((prev) => ({ ...prev, [adapter.id]: health }));
    } catch (e) {
      setMessage(String(e));
    } finally {
      setCheckingId(null);
    }
  };

  const deleteAdapter = async (adapter: Adapter) => {
    if (!confirm(`确认删除适配器「${adapter.name}」？`)) return;
    try {
      await api.deleteAdapter(adapter.id);
      load();
    } catch (e) {
      setMessage(String(e));
    }
  };

  return (
    <AppShell title="Agent 接入">
      {/* 接入指引 */}
      <div className="mb-6 bg-indigo-50 border border-indigo-100 rounded-lg p-5">
        <h3 className="text-sm font-semibold text-indigo-900 mb-2">统一接入协议</h3>
        <div className="text-sm text-indigo-800 space-y-1">
          <p>
            <span className="font-medium">Push 模式：</span>
            平台 POST 任务至 Agent 的 <code className="text-xs bg-white px-1 rounded">/v1/tasks</code>，
            Agent 完成后回调 <code className="text-xs bg-white px-1 rounded">{API_URL}/v1/webhooks/agent_feedback</code>
          </p>
          <p>
            <span className="font-medium">Pull 模式：</span>
            Agent 轮询 <code className="text-xs bg-white px-1 rounded">{API_URL}/v1/agent/pull?adapter_name=&#123;name&#125;</code> 拉取任务
          </p>
          <p className="text-xs text-indigo-700 mt-2">
            SDK 与 HMAC 签名说明见 <code>docs/agent-sdk.md</code>，Pull 客户端见 <code>packages/agent-sdk</code>
          </p>
        </div>
      </div>

      <div className="flex justify-between items-center mb-6">
        <p className="text-sm text-gray-500">共 {adapters.length} 个适配器</p>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700"
        >
          新建适配器
        </button>
      </div>

      {message && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">{message}</div>
      )}

      {adapters.length === 0 && !showForm && (
        <div className="text-center py-16 text-gray-400">
          <p className="mb-4">暂无 Agent 适配器</p>
          <button onClick={openCreate} className="text-indigo-600 hover:text-indigo-800 text-sm">
            创建第一个适配器
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {adapters.map((adapter) => {
          const health = healthMap[adapter.id];
          return (
            <div key={adapter.id} className="bg-white rounded-lg shadow border border-gray-200 p-6 flex flex-col">
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-lg font-bold">{adapter.name}</h3>
                <span
                  className={`px-2 py-1 text-xs rounded-full ${
                    adapter.is_online ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {adapter.is_online ? "Online" : "Offline"}
                </span>
              </div>
              <p className="text-sm text-gray-500 mb-1">{adapter.adapter_type}</p>
              <p className="text-sm text-gray-600 mb-3 flex-1">{adapter.description || "—"}</p>
              <div className="text-xs text-gray-500 space-y-1 mb-4">
                <p>协议: {adapter.protocol === "push" ? "Webhook (Push)" : "Polling (Pull)"}</p>
                <p className="truncate" title={adapter.endpoint}>
                  Endpoint: {adapter.endpoint}
                </p>
                {adapter.protocol === "pull" && (
                  <p className="truncate" title={`${API_URL}/v1/agent/pull?adapter_name=${adapter.name}`}>
                    Pull URL: /v1/agent/pull?adapter_name={adapter.name}
                  </p>
                )}
              </div>

              {health && (
                <div
                  className={`text-xs p-2 rounded mb-3 ${
                    health.status === "ok" ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"
                  }`}
                >
                  健康检查: {health.status === "ok" ? "正常" : "异常"}
                  {health.latency_ms != null && ` · ${health.latency_ms}ms`}
                  {health.queue_depth != null && ` · 队列 ${health.queue_depth}`}
                  {health.error && ` · ${health.error}`}
                </div>
              )}

              <div className="flex flex-wrap gap-3 text-sm">
                <button
                  onClick={() => checkHealth(adapter)}
                  disabled={checkingId === adapter.id}
                  className="text-indigo-600 hover:text-indigo-900 disabled:opacity-50"
                >
                  {checkingId === adapter.id ? "检测中…" : "健康检查"}
                </button>
                <button onClick={() => openEdit(adapter)} className="text-gray-600 hover:text-gray-900">
                  编辑
                </button>
                <button onClick={() => toggleOnline(adapter)} className="text-gray-600 hover:text-gray-900">
                  {adapter.is_online ? "停用" : "启用"}
                </button>
                <button onClick={() => deleteAdapter(adapter)} className="text-red-500 hover:text-red-700">
                  删除
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* 创建/编辑表单 */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
            <h3 className="text-lg font-bold mb-4">{editing ? "编辑适配器" : "新建适配器"}</h3>
            <div className="space-y-4">
              <div>
                <FieldLabel>名称</FieldLabel>
                <input
                  className={inputClass}
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="如 OpenClaw"
                />
              </div>
              <div>
                <FieldLabel>类型</FieldLabel>
                <select
                  className={inputClass}
                  value={form.adapter_type}
                  onChange={(e) => setForm({ ...form, adapter_type: e.target.value })}
                >
                  <option value="generic">generic — 标准协议</option>
                  <option value="coze">coze — 扣子 Bot</option>
                  <option value="dify">dify — Dify Workflow</option>
                </select>
              </div>
              <div>
                <FieldLabel hint="push=平台推送，pull=Agent 拉取">协议</FieldLabel>
                <select
                  className={inputClass}
                  value={form.protocol}
                  onChange={(e) => setForm({ ...form, protocol: e.target.value as "push" | "pull" })}
                >
                  <option value="push">Push (Webhook)</option>
                  <option value="pull">Pull (Polling)</option>
                </select>
              </div>
              <div>
                <FieldLabel hint={form.protocol === "push" ? "Agent 接收任务的基地址" : "Agent 服务地址（信息性）"}>
                  Endpoint
                </FieldLabel>
                <input
                  className={inputClass}
                  value={form.endpoint}
                  onChange={(e) => setForm({ ...form, endpoint: e.target.value })}
                  placeholder="http://localhost:8100"
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
                <FieldLabel hint='如 {"bearer_token":"..."} 或 {"api_key":"...","webhook_secret":"..."}'>
                  鉴权配置 (JSON)
                </FieldLabel>
                <textarea
                  className={`${inputClass} font-mono text-xs`}
                  rows={3}
                  value={authJson}
                  onChange={(e) => setAuthJson(e.target.value)}
                />
              </div>
              <div>
                <FieldLabel hint='如 {"completed":"success","error":"failed"}'>
                  状态映射 (JSON)
                </FieldLabel>
                <textarea
                  className={`${inputClass} font-mono text-xs`}
                  rows={2}
                  value={mappingJson}
                  onChange={(e) => setMappingJson(e.target.value)}
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_online}
                  onChange={(e) => setForm({ ...form, is_online: e.target.checked })}
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
                onClick={saveAdapter}
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
