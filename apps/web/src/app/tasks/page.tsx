"use client";

import { AppShell } from "@/components/layout/app-shell";
import { api, Adapter, Task } from "@/lib/api";
import { useEffect, useState } from "react";

const statusClass: Record<string, string> = {
  Running: "bg-blue-100 text-blue-800",
  Success: "bg-green-100 text-green-800",
  Failed: "bg-red-100 text-red-800",
  Draft: "bg-gray-100 text-gray-800",
  Ready: "bg-yellow-100 text-yellow-800",
};

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [adapters, setAdapters] = useState<Adapter[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", objective: "", agent_adapter_id: "" });
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [message, setMessage] = useState("");

  const load = () => {
    api.listTasks({ search: search || undefined, status: statusFilter || undefined }).then((r) => setTasks(r.items));
    api.listAdapters().then(setAdapters);
  };

  useEffect(() => { load(); }, [search, statusFilter]);

  const createAndSubmit = async () => {
    try {
      const task = await api.createTask({
        name: form.name,
        objective: form.objective,
        agent_adapter_id: form.agent_adapter_id || undefined,
      });
      const run = await api.submitTask(task.id);
      setMessage(`任务已提交: ${task.name}, run=${run.id.slice(0, 8)}`);
      setShowForm(false);
      setForm({ name: "", objective: "", agent_adapter_id: "" });
      load();
    } catch (e) {
      setMessage(String(e));
    }
  };

  const viewLogs = async (taskId: string) => {
    const detail = await api.getTask(taskId);
    if (detail.latest_run) {
      setSelectedRun(detail.latest_run.id);
      const logData = await api.getRunLogs(detail.latest_run.id);
      setLogs(logData.logs.map((l) => `[${l.source}] ${l.message}`));
    } else {
      setLogs(["暂无执行记录"]);
    }
  };

  const terminate = async (taskId: string) => {
    const detail = await api.getTask(taskId);
    if (detail.latest_run) {
      await api.terminateRun(detail.latest_run.id);
      setMessage("任务已终止");
      load();
    }
  };

  const retry = async (taskId: string) => {
    const detail = await api.getTask(taskId);
    if (detail.latest_run) {
      await api.retryRun(detail.latest_run.id);
      setMessage("已触发重试");
      load();
    }
  };

  return (
    <AppShell title="任务中心">
      {message && (
        <div className="mb-4 bg-indigo-50 text-indigo-800 px-4 py-2 rounded text-sm">{message}</div>
      )}
      <div className="flex justify-between items-center mb-6">
        <div className="flex space-x-2">
          <input
            type="text"
            placeholder="搜索任务..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border rounded-md text-sm py-2 px-4 border-gray-300"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border rounded-md text-sm py-2 px-4 border-gray-300"
          >
            <option value="">全部状态</option>
            <option value="Draft">Draft</option>
            <option value="Ready">Ready</option>
            <option value="Running">Running</option>
            <option value="Success">Success</option>
            <option value="Failed">Failed</option>
          </select>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700"
        >
          新建任务
        </button>
      </div>

      {showForm && (
        <div className="mb-6 bg-white p-6 rounded-lg shadow border">
          <h3 className="font-medium mb-4">新建任务</h3>
          <div className="grid gap-3 max-w-lg">
            <input placeholder="任务名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <textarea placeholder="任务目标" value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })} className="border rounded px-3 py-2 text-sm" rows={3} />
            <select value={form.agent_adapter_id} onChange={(e) => setForm({ ...form, agent_adapter_id: e.target.value })} className="border rounded px-3 py-2 text-sm">
              <option value="">选择 Agent</option>
              {adapters.map((a) => (
                <option key={a.id} value={a.id}>{a.name} ({a.protocol})</option>
              ))}
            </select>
            <div className="flex gap-2">
              <button onClick={createAndSubmit} className="bg-indigo-600 text-white px-4 py-2 rounded text-sm">创建并提交</button>
              <button onClick={() => setShowForm(false)} className="border px-4 py-2 rounded text-sm">取消</button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white shadow rounded-lg border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">任务 ID / 名称</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agent</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {tasks.map((task) => {
              const adapter = adapters.find((a) => a.id === task.agent_adapter_id);
              return (
                <tr key={task.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium">{task.name}</div>
                    <div className="text-sm text-gray-500 font-mono">{task.id.slice(0, 8)}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${statusClass[task.status] || "bg-gray-100"}`}>
                      {task.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{adapter?.name || "-"}</td>
                  <td className="px-6 py-4 text-right text-sm space-x-2">
                    <button onClick={() => viewLogs(task.id)} className="text-indigo-600 hover:text-indigo-900">日志</button>
                    <button onClick={() => retry(task.id)} className="text-gray-600">重试</button>
                    <button onClick={() => terminate(task.id)} className="text-red-600">终止</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selectedRun && (
        <div className="mt-6 bg-white p-4 rounded-lg border">
          <h4 className="font-medium mb-2">执行日志 (run: {selectedRun.slice(0, 8)})</h4>
          <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto max-h-48">{logs.join("\n")}</pre>
        </div>
      )}
    </AppShell>
  );
}
