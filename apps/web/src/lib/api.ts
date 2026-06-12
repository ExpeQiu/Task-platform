const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  getDashboard: () => request<DashboardMetrics>("/v1/metrics/dashboard"),
  listTasks: (params?: { status?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.search) q.set("search", params.search);
    return request<TaskListResponse>(`/v1/tasks?${q}`);
  },
  getTask: (id: string) => request<TaskDetail>(`/v1/tasks/${id}`),
  createTask: (body: TaskCreate) =>
    request<Task>("/v1/tasks", { method: "POST", body: JSON.stringify(body) }),
  submitTask: (id: string) =>
    request<TaskRun>(`/v1/tasks/${id}/submit`, { method: "POST" }),
  getRun: (id: string) => request<TaskRun>(`/v1/runs/${id}`),
  getRunLogs: (id: string) => request<RunLogs>(`/v1/runs/${id}/logs`),
  retryRun: (id: string) => request<TaskRun>(`/v1/runs/${id}/retry`, { method: "POST" }),
  terminateRun: (id: string) => request<TaskRun>(`/v1/runs/${id}/terminate`, { method: "POST" }),
  listAlerts: () => request<Alert[]>("/v1/alerts"),
  updateAlert: (id: string, status: string) =>
    request<Alert>(`/v1/alerts/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  listAudit: () => request<AuditEvent[]>("/v1/audit"),
  exportAudit: () => `${API_URL}/v1/audit/export`,
  listAdapters: () => request<Adapter[]>("/v1/adapters"),
  createAdapter: (body: Partial<Adapter>) =>
    request<Adapter>("/v1/adapters", { method: "POST", body: JSON.stringify(body) }),
  updateAdapter: (id: string, body: Partial<Adapter>) =>
    request<Adapter>(`/v1/adapters/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
};

export interface DashboardMetrics {
  total_tasks: number;
  active_runs: number;
  success_rate: number;
  queue_backlog: number;
  trend: { hour: string; success: number; failed: number }[];
  agent_distribution: { name: string; count: number }[];
}

export interface Task {
  id: string;
  name: string;
  objective: string;
  priority: number;
  sla_seconds: number;
  tags: string[];
  agent_adapter_id: string | null;
  status: string;
  created_at: string;
}

export interface TaskRun {
  id: string;
  task_id: string;
  status: string;
  progress: number;
  iteration_count: number;
  error_message: string | null;
}

export interface TaskDetail extends Task {
  latest_run: TaskRun | null;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
}

export interface TaskCreate {
  name: string;
  objective: string;
  agent_adapter_id?: string;
  sla_seconds?: number;
  tags?: string[];
}

export interface RunLogs {
  run_id: string;
  logs: { timestamp: string; source: string; message: string; metadata: Record<string, unknown> }[];
}

export interface Alert {
  id: string;
  severity: string;
  alert_type: string;
  content: string;
  status: string;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  actor: string;
  action: string;
  target: string;
  detail: string;
  created_at: string;
}

export interface Adapter {
  id: string;
  name: string;
  adapter_type: string;
  protocol: string;
  endpoint: string;
  description: string;
  is_online: boolean;
}
