"use client";

import { AppShell } from "@/components/layout/app-shell";
import { api, MemoryEntry } from "@/lib/api";
import { useEffect, useState } from "react";

const inputClass = "w-full border border-gray-300 rounded-md px-3 py-2 text-sm";
const SCOPES = ["global", "task_type", "task"] as const;

export default function MemoryPage() {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [scopeFilter, setScopeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({ scope: "global", scope_ref: "", key: "", content: "" });
  const [showForm, setShowForm] = useState(false);
  const [message, setMessage] = useState("");

  const load = () => {
    api
      .listMemory({ scope: scopeFilter || undefined, search: search || undefined })
      .then(setEntries)
      .catch(console.error);
  };

  useEffect(() => { load(); }, [scopeFilter, search]);

  const create = async () => {
    if (!form.key.trim() || !form.content.trim()) {
      setMessage("请填写 key 和 content");
      return;
    }
    try {
      await api.createMemory({
        scope: form.scope,
        scope_ref: form.scope_ref || undefined,
        key: form.key,
        content: form.content,
      });
      setForm({ scope: "global", scope_ref: "", key: "", content: "" });
      setShowForm(false);
      setMessage("记忆已保存");
      load();
    } catch (e) {
      setMessage(String(e));
    }
  };

  return (
    <AppShell title="长期记忆">
      {message && <div className="mb-4 bg-indigo-50 text-indigo-800 px-4 py-2 rounded text-sm">{message}</div>}
      <div className="flex flex-wrap gap-3 mb-6 items-center justify-between">
        <div className="flex gap-2">
          <select
            value={scopeFilter}
            onChange={(e) => setScopeFilter(e.target.value)}
            className="border rounded-md text-sm py-2 px-3"
          >
            <option value="">全部 scope</option>
            {SCOPES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <input
            placeholder="搜索 key / content"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border rounded-md text-sm py-2 px-3"
          />
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm"
        >
          新增记忆
        </button>
      </div>

      {showForm && (
        <div className="mb-6 bg-white p-4 rounded-lg border space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <select
              className={inputClass}
              value={form.scope}
              onChange={(e) => setForm({ ...form, scope: e.target.value })}
            >
              {SCOPES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <input
              className={inputClass}
              placeholder="scope_ref（可选）"
              value={form.scope_ref}
              onChange={(e) => setForm({ ...form, scope_ref: e.target.value })}
            />
          </div>
          <input
            className={inputClass}
            placeholder="key"
            value={form.key}
            onChange={(e) => setForm({ ...form, key: e.target.value })}
          />
          <textarea
            className={inputClass}
            rows={4}
            placeholder="content"
            value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
          />
          <div className="flex gap-2">
            <button onClick={create} className="bg-indigo-600 text-white px-4 py-2 rounded text-sm">保存</button>
            <button onClick={() => setShowForm(false)} className="border px-4 py-2 rounded text-sm">取消</button>
          </div>
        </div>
      )}

      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-gray-500">Scope</th>
              <th className="px-4 py-2 text-left text-gray-500">Key</th>
              <th className="px-4 py-2 text-left text-gray-500">Content</th>
              <th className="px-4 py-2 text-left text-gray-500">时间</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {entries.map((e) => (
              <tr key={e.id}>
                <td className="px-4 py-2">
                  <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{e.scope}</span>
                  {e.scope_ref && <span className="text-xs text-gray-400 ml-1">{e.scope_ref}</span>}
                </td>
                <td className="px-4 py-2 font-mono text-xs">{e.key}</td>
                <td className="px-4 py-2 text-gray-600 max-w-md truncate">{e.content}</td>
                <td className="px-4 py-2 text-gray-400 text-xs">{new Date(e.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {entries.length === 0 && <p className="p-6 text-center text-gray-500">暂无记忆条目</p>}
      </div>
    </AppShell>
  );
}
