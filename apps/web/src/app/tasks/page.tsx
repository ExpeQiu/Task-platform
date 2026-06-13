"use client";

import { AppShell } from "@/components/layout/app-shell";
import { CriteriaBuilder } from "@/components/tasks/criteria-builder";
import { api, Adapter, CriteriaConfig, Skill, TaskCreate, TaskListItem } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const statusClass: Record<string, string> = {
  Running: "bg-blue-100 text-blue-800",
  Success: "bg-green-100 text-green-800",
  Failed: "bg-red-100 text-red-800",
  Draft: "bg-gray-100 text-gray-800",
  Ready: "bg-yellow-100 text-yellow-800",
  Scheduled: "bg-indigo-100 text-indigo-800",
  WaitingFeedback: "bg-purple-100 text-purple-800",
  Reviewing: "bg-cyan-100 text-cyan-800",
  Iterating: "bg-orange-100 text-orange-800",
  Cancelled: "bg-gray-100 text-gray-600",
  Terminated: "bg-red-50 text-red-700",
};

const VERIFICATION_LABELS: Record<string, string> = {
  rule_based: "规则",
  llm_agent: "LLM",
  hybrid: "混合",
};

const DEFAULT_CRITERIA: CriteriaConfig = { rules: [], match: "all" };

const DEFAULT_FORM = {
  name: "",
  objective: "",
  agent_adapter_id: "",
  priority: 5,
  sla_seconds: 300,
  tags: "",
  schedule_mode: "immediate" as "immediate" | "once" | "cron",
  schedule_at: "",
  schedule_cron: "",
  loop_max_iterations: 10,
  loop_max_duration_seconds: 3600,
  loop_no_progress_threshold: "" as number | "",
  loop_budget_limit: "" as number | "",
  retry_max_retries: 3,
  retry_backoff_base_seconds: 30,
  criteria: DEFAULT_CRITERIA,
  verification_mode: "rule_based" as "rule_based" | "llm_agent" | "hybrid",
  skill_id: "",
};

type TaskForm = typeof DEFAULT_FORM;

function parseTags(raw: string): string[] {
  return raw
    .split(/[,，]/)
    .map((t) => t.trim())
    .filter(Boolean);
}

function buildPayload(form: TaskForm): TaskCreate {
  const payload: TaskCreate = {
    name: form.name.trim(),
    objective: form.objective.trim(),
    priority: form.priority,
    sla_seconds: form.sla_seconds,
    tags: parseTags(form.tags),
    loop_config: {
      max_iterations: form.loop_max_iterations,
      max_duration_seconds: form.loop_max_duration_seconds,
      no_progress_threshold: form.loop_no_progress_threshold === "" ? null : form.loop_no_progress_threshold,
      budget_limit: form.loop_budget_limit === "" ? null : form.loop_budget_limit,
    },
    retry_config: {
      max_retries: form.retry_max_retries,
      backoff_base_seconds: form.retry_backoff_base_seconds,
    },
  };

  if (form.criteria?.rules?.length) {
    payload.success_criteria = form.criteria;
  }

  if (form.agent_adapter_id) payload.agent_adapter_id = form.agent_adapter_id;
  if (form.verification_mode) payload.verification_mode = form.verification_mode;
  if (form.skill_id) payload.skill_id = form.skill_id;

  if (form.schedule_mode === "once" && form.schedule_at) {
    payload.schedule_at = new Date(form.schedule_at).toISOString();
  } else if (form.schedule_mode === "cron" && form.schedule_cron.trim()) {
    payload.schedule_cron = form.schedule_cron.trim();
  }

  return payload;
}

function FieldLabel({ children, hint }: { children: React.ReactNode; hint?: string }) {
  return (
    <label className="block text-sm font-medium text-gray-700 mb-1">
      {children}
      {hint && <span className="ml-1 text-xs font-normal text-gray-400">{hint}</span>}
    </label>
  );
}

const inputClass = "w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500";

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [adapters, setAdapters] = useState<Adapter[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [form, setForm] = useState<TaskForm>({ ...DEFAULT_FORM, criteria: { ...DEFAULT_CRITERIA } });
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    api.listTasks({ search: search || undefined, status: statusFilter || undefined }).then((r) => setTasks(r.items));
    api.listAdapters().then(setAdapters);
    api.listSkills().then((r) => setSkills(r.items.filter((s) => s.is_active))).catch(() => {});
  };

  useEffect(() => { load(); }, [search, statusFilter]);

  const resetForm = () => {
    setForm({ ...DEFAULT_FORM, criteria: { ...DEFAULT_CRITERIA } });
    setShowAdvanced(false);
  };

  const validateForm = (): string | null => {
    if (!form.name.trim()) return "请填写任务名称";
    if (!form.objective.trim()) return "请填写任务目标";
    if (form.schedule_mode === "once" && !form.schedule_at) return "请选择定时执行时间";
    if (form.schedule_mode === "cron" && !form.schedule_cron.trim()) return "请填写 Cron 表达式";
    return null;
  };

  const createTask = async (submit: boolean) => {
    const err = validateForm();
    if (err) {
      setMessage(err);
      return;
    }
    setSubmitting(true);
    try {
      const task = await api.createTask(buildPayload(form));
      if (submit) {
        const run = await api.submitTask(task.id);
        setMessage(`任务已提交: ${task.name}, run=${run.id.slice(0, 8)}`);
      } else {
        setMessage(`草稿已保存: ${task.name}`);
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

  const openRun = (task: TaskListItem) => {
    if (task.latest_run) {
      router.push(`/runs/${task.latest_run.id}`);
    } else {
      setMessage("暂无执行记录");
    }
  };

  const terminate = async (task: TaskListItem) => {
    if (task.latest_run) {
      await api.terminateRun(task.latest_run.id);
      setMessage("任务已终止");
      load();
    }
  };

  const retry = async (task: TaskListItem) => {
    if (task.latest_run) {
      await api.retryRun(task.latest_run.id);
      setMessage("已触发重试");
      load();
    }
  };

  const selectedAdapter = adapters.find((a) => a.id === form.agent_adapter_id);

  return (
    <AppShell title="任务中心">
      {message && (
        <div className="mb-4 bg-indigo-50 text-indigo-800 px-4 py-2 rounded text-sm flex justify-between items-center">
          <span>{message}</span>
          <button onClick={() => setMessage("")} className="text-indigo-600 hover:text-indigo-800 ml-4">×</button>
        </div>
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
            <option value="Scheduled">Scheduled</option>
            <option value="Running">Running</option>
            <option value="WaitingFeedback">WaitingFeedback</option>
            <option value="Reviewing">Reviewing</option>
            <option value="Iterating">Iterating</option>
            <option value="Success">Success</option>
            <option value="Failed">Failed</option>
            <option value="Terminated">Terminated</option>
          </select>
        </div>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700"
        >
          新建任务
        </button>
      </div>

      {showForm && (
        <div className="mb-6 bg-white p-6 rounded-lg shadow border">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-lg font-medium text-gray-900">新建任务</h3>
            <button onClick={() => { setShowForm(false); resetForm(); }} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide border-b pb-2">基础信息</h4>
              <div>
                <FieldLabel>任务名称</FieldLabel>
                <input
                  placeholder="例如：每日竞品监控报告"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className={inputClass}
                />
              </div>
              <div>
                <FieldLabel>任务目标</FieldLabel>
                <textarea
                  placeholder="描述 Agent 需要完成的具体目标与预期产出..."
                  value={form.objective}
                  onChange={(e) => setForm({ ...form, objective: e.target.value })}
                  className={inputClass}
                  rows={4}
                />
              </div>
              <div>
                <FieldLabel hint="rule_based | llm_agent | hybrid">验证模式</FieldLabel>
                <select
                  value={form.verification_mode}
                  onChange={(e) => setForm({ ...form, verification_mode: e.target.value as TaskForm["verification_mode"] })}
                  className={inputClass}
                >
                  <option value="rule_based">规则验证（默认）</option>
                  <option value="llm_agent">独立 LLM Verifier</option>
                  <option value="hybrid">规则 + LLM 混合</option>
                </select>
              </div>
              <div>
                <FieldLabel hint="可选">关联 Skill</FieldLabel>
                <select
                  value={form.skill_id}
                  onChange={(e) => setForm({ ...form, skill_id: e.target.value })}
                  className={inputClass}
                >
                  <option value="">不使用 Skill</option>
                  {skills.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
                {skills.length === 0 && (
                  <p className="mt-1 text-xs text-gray-400">
                    暂无 Skill，可在 <Link href="/skills" className="text-indigo-600 hover:underline">Skill 资产</Link> 中创建
                  </p>
                )}
              </div>
              <CriteriaBuilder
                value={form.criteria}
                onChange={(criteria) => setForm({ ...form, criteria })}
              />
              <div>
                <FieldLabel hint="逗号分隔">标签</FieldLabel>
                <input
                  placeholder="monitoring, daily, report"
                  value={form.tags}
                  onChange={(e) => setForm({ ...form, tags: e.target.value })}
                  className={inputClass}
                />
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide border-b pb-2">执行配置</h4>
              <div>
                <FieldLabel>分配 Agent</FieldLabel>
                <select
                  value={form.agent_adapter_id}
                  onChange={(e) => setForm({ ...form, agent_adapter_id: e.target.value })}
                  className={inputClass}
                >
                  <option value="">自动分配</option>
                  {adapters.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.protocol}){a.is_online ? "" : " [离线]"}
                    </option>
                  ))}
                </select>
                {selectedAdapter && (
                  <p className="mt-1.5 text-xs text-gray-500">
                    {selectedAdapter.description || "无描述"} · {selectedAdapter.adapter_type} · {selectedAdapter.is_online ? "在线" : "离线"}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <FieldLabel hint="1-10，数值越大越优先">优先级</FieldLabel>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={form.priority}
                    onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
                    className={inputClass}
                  />
                </div>
                <div>
                  <FieldLabel hint="超时告警阈值">SLA (秒)</FieldLabel>
                  <input
                    type="number"
                    min={30}
                    step={30}
                    value={form.sla_seconds}
                    onChange={(e) => setForm({ ...form, sla_seconds: Number(e.target.value) })}
                    className={inputClass}
                  />
                </div>
              </div>

              <div>
                <FieldLabel>调度方式</FieldLabel>
                <div className="flex flex-wrap gap-2 mb-2">
                  {([
                    ["immediate", "立即执行"],
                    ["once", "定时一次"],
                    ["cron", "Cron 周期"],
                  ] as const).map(([mode, label]) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setForm({ ...form, schedule_mode: mode })}
                      className={`px-3 py-1.5 rounded-md text-sm border transition ${
                        form.schedule_mode === mode
                          ? "bg-indigo-50 border-indigo-500 text-indigo-700"
                          : "border-gray-300 text-gray-600 hover:bg-gray-50"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {form.schedule_mode === "once" && (
                  <input
                    type="datetime-local"
                    value={form.schedule_at}
                    onChange={(e) => setForm({ ...form, schedule_at: e.target.value })}
                    className={inputClass}
                  />
                )}
                {form.schedule_mode === "cron" && (
                  <input
                    placeholder="0 9 * * * (每天 9:00)"
                    value={form.schedule_cron}
                    onChange={(e) => setForm({ ...form, schedule_cron: e.target.value })}
                    className={inputClass}
                  />
                )}
              </div>
            </div>
          </div>

          <div className="mt-5 border-t pt-4">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
            >
              <span className={`inline-block transition-transform ${showAdvanced ? "rotate-90" : ""}`}>▶</span>
              高级配置：循环控制 & 重试策略
            </button>
            {showAdvanced && (
              <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <h5 className="text-xs font-semibold text-gray-500 uppercase">循环兜底</h5>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <FieldLabel hint="防止无限循环">最大迭代次数</FieldLabel>
                      <input type="number" min={1} value={form.loop_max_iterations}
                        onChange={(e) => setForm({ ...form, loop_max_iterations: Number(e.target.value) })}
                        className={inputClass} />
                    </div>
                    <div>
                      <FieldLabel hint="超时强制终止">最大时长 (秒)</FieldLabel>
                      <input type="number" min={60} value={form.loop_max_duration_seconds}
                        onChange={(e) => setForm({ ...form, loop_max_duration_seconds: Number(e.target.value) })}
                        className={inputClass} />
                    </div>
                    <div>
                      <FieldLabel hint="可选">无进展阈值</FieldLabel>
                      <input type="number" min={1} placeholder="留空不限"
                        value={form.loop_no_progress_threshold}
                        onChange={(e) => setForm({ ...form, loop_no_progress_threshold: e.target.value ? Number(e.target.value) : "" })}
                        className={inputClass} />
                    </div>
                    <div>
                      <FieldLabel hint="可选">资源预算上限</FieldLabel>
                      <input type="number" min={1} placeholder="留空不限"
                        value={form.loop_budget_limit}
                        onChange={(e) => setForm({ ...form, loop_budget_limit: e.target.value ? Number(e.target.value) : "" })}
                        className={inputClass} />
                    </div>
                  </div>
                </div>
                <div className="space-y-3">
                  <h5 className="text-xs font-semibold text-gray-500 uppercase">重试策略</h5>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <FieldLabel>最大重试次数</FieldLabel>
                      <input type="number" min={0} max={10} value={form.retry_max_retries}
                        onChange={(e) => setForm({ ...form, retry_max_retries: Number(e.target.value) })}
                        className={inputClass} />
                    </div>
                    <div>
                      <FieldLabel hint="指数退避基数">退避间隔 (秒)</FieldLabel>
                      <input type="number" min={5} step={5} value={form.retry_backoff_base_seconds}
                        onChange={(e) => setForm({ ...form, retry_backoff_base_seconds: Number(e.target.value) })}
                        className={inputClass} />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="mt-6 flex gap-2 pt-4 border-t">
            <button
              onClick={() => createTask(true)}
              disabled={submitting}
              className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {submitting ? "提交中..." : "创建并提交"}
            </button>
            <button
              onClick={() => createTask(false)}
              disabled={submitting}
              className="border border-gray-300 text-gray-700 px-4 py-2 rounded-md text-sm hover:bg-gray-50 disabled:opacity-50"
            >
              保存草稿
            </button>
            <button
              onClick={() => { setShowForm(false); resetForm(); }}
              className="border border-gray-300 text-gray-500 px-4 py-2 rounded-md text-sm hover:bg-gray-50"
            >
              取消
            </button>
          </div>
        </div>
      )}

      <div className="bg-white shadow rounded-lg border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">任务 ID / 名称</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">验证</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">轮次</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">优先级</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agent</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">标签</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {tasks.map((task) => {
              const adapter = adapters.find((a) => a.id === task.agent_adapter_id);
              const runStatus = task.latest_run?.status;
              const displayStatus = runStatus && task.status === "Ready" ? runStatus : task.status;
              return (
                <tr key={task.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium">{task.name}</div>
                    <div className="text-sm text-gray-500 font-mono">{task.id.slice(0, 8)}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${statusClass[displayStatus] || "bg-gray-100"}`}>
                      {displayStatus}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {VERIFICATION_LABELS[task.verification_mode || "rule_based"] || task.verification_mode || "规则"}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {task.latest_run ? (
                      <button
                        type="button"
                        onClick={() => openRun(task)}
                        className="text-indigo-600 hover:underline"
                      >
                        第 {task.latest_run.iteration_count} 轮
                      </button>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                      task.priority >= 8 ? "bg-red-100 text-red-700" : task.priority >= 5 ? "bg-yellow-100 text-yellow-700" : "bg-gray-100 text-gray-600"
                    }`}>
                      {task.priority}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{adapter?.name || "-"}</td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {task.tags?.length ? task.tags.map((tag) => (
                        <span key={tag} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">{tag}</span>
                      )) : <span className="text-sm text-gray-400">-</span>}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right text-sm space-x-2">
                    {task.latest_run ? (
                      <Link href={`/runs/${task.latest_run.id}`} className="text-indigo-600 hover:text-indigo-900">详情</Link>
                    ) : (
                      <span className="text-gray-400">详情</span>
                    )}
                    <button onClick={() => retry(task)} className="text-gray-600">重试</button>
                    <button onClick={() => terminate(task)} className="text-red-600">终止</button>
                  </td>
                </tr>
              );
            })}
            {tasks.length === 0 && (
              <tr><td colSpan={8} className="px-6 py-8 text-center text-gray-500">暂无任务</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
