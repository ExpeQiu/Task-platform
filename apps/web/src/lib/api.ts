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
  getAdapterMetrics: () => request<AdapterStat[]>("/v1/metrics/adapters"),
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
  getRunTimeline: (id: string) => request<RunTimeline>(`/v1/runs/${id}/timeline`),
  retryRun: (id: string) => request<TaskRun>(`/v1/runs/${id}/retry`, { method: "POST" }),
  terminateRun: (id: string) => request<TaskRun>(`/v1/runs/${id}/terminate`, { method: "POST" }),
  listAlerts: (params?: { alert_type?: string }) => {
    const q = new URLSearchParams();
    if (params?.alert_type) q.set("alert_type", params.alert_type);
    const qs = q.toString();
    return request<Alert[]>(`/v1/alerts${qs ? `?${qs}` : ""}`);
  },
  updateAlert: (id: string, status: string) =>
    request<Alert>(`/v1/alerts/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  listAudit: () => request<AuditEvent[]>("/v1/audit"),
  exportAudit: () => `${API_URL}/v1/audit/export`,
  listAdapters: () => request<Adapter[]>("/v1/adapters"),
  getAdapter: (id: string) => request<Adapter>(`/v1/adapters/${id}`),
  createAdapter: (body: AdapterCreate) =>
    request<Adapter>("/v1/adapters", { method: "POST", body: JSON.stringify(body) }),
  updateAdapter: (id: string, body: AdapterUpdate) =>
    request<Adapter>(`/v1/adapters/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteAdapter: (id: string) =>
    request<void>(`/v1/adapters/${id}`, { method: "DELETE" }),
  checkAdapterHealth: (id: string) => request<AdapterHealth>(`/v1/adapters/${id}/health`),

  // MCP
  listMcpServers: () => request<McpServer[]>("/v1/mcp"),
  getMcpServer: (id: string) => request<McpServer>(`/v1/mcp/${id}`),
  createMcpServer: (body: McpServerCreate) =>
    request<McpServer>("/v1/mcp", { method: "POST", body: JSON.stringify(body) }),
  updateMcpServer: (id: string, body: McpServerUpdate) =>
    request<McpServer>(`/v1/mcp/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteMcpServer: (id: string) => request<void>(`/v1/mcp/${id}`, { method: "DELETE" }),
  probeMcpServer: (id: string) => request<McpHealth>(`/v1/mcp/${id}/probe`, { method: "POST" }),

  // Skills
  listSkills: () => request<SkillListResponse>("/v1/skills"),
  createSkill: (body: SkillCreate) =>
    request<Skill>("/v1/skills", { method: "POST", body: JSON.stringify(body) }),
  updateSkill: (id: string, body: Partial<SkillCreate>) =>
    request<Skill>(`/v1/skills/${id}`, { method: "PATCH", body: JSON.stringify(body) }),

  // Memory
  listMemory: (params?: { scope?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.scope) q.set("scope", params.scope);
    if (params?.search) q.set("search", params.search);
    return request<MemoryEntry[]>(`/v1/memory?${q}`);
  },
  createMemory: (body: { scope?: string; scope_ref?: string; key: string; content: string }) =>
    request<MemoryEntry>("/v1/memory", { method: "POST", body: JSON.stringify(body) }),

  // Approvals
  listPendingApprovals: () => request<PendingApproval[]>("/v1/workflows/approvals/pending"),
  listRunApprovals: (runId: string) => request<WorkflowApproval[]>(`/v1/workflows/runs/${runId}/approvals`),
  decideApproval: (runId: string, approvalId: string, body: { approved: boolean; note?: string; actor?: string }) =>
    request<WorkflowRun>(`/v1/workflows/runs/${runId}/approvals/${approvalId}/decide`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Workflows / Orchestrator
  listWorkflows: (params?: { status?: string }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    return request<WorkflowListResponse>(`/v1/workflows?${q}`);
  },
  getWorkflow: (id: string) => request<Workflow>(`/v1/workflows/${id}`),
  createWorkflow: (body: WorkflowCreate) =>
    request<Workflow>("/v1/workflows", { method: "POST", body: JSON.stringify(body) }),
  updateWorkflow: (id: string, body: WorkflowUpdate) =>
    request<Workflow>(`/v1/workflows/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  validateWorkflow: (id: string) =>
    request<WorkflowValidateResult>(`/v1/workflows/${id}/validate`, { method: "POST" }),
  publishWorkflow: (id: string) =>
    request<Workflow>(`/v1/workflows/${id}/publish`, { method: "POST" }),
  triggerWorkflow: (id: string, context?: Record<string, unknown>) =>
    request<WorkflowRun>(`/v1/workflows/${id}/trigger`, {
      method: "POST",
      body: JSON.stringify({ context: context || {} }),
    }),
  listWorkflowRuns: (id: string) => request<WorkflowRun[]>(`/v1/workflows/${id}/runs`),
  getWorkflowRun: (id: string) => request<WorkflowRun>(`/v1/workflows/runs/${id}`),
  aiOrchestratorChat: (body: AiOrchestratorRequest) =>
    request<AiOrchestratorResponse>("/v1/workflows/ai/chat", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export interface DashboardMetrics {
  total_tasks: number;
  active_runs: number;
  success_rate: number;
  queue_backlog: number;
  trend: { hour: string; success: number; failed: number }[];
  agent_distribution: { name: string; count: number }[];
  adapter_stats: AdapterStat[];
  loop_stats?: {
    no_progress_alerts?: number;
    budget_exceeded_alerts?: number;
    llm_verifications?: number;
    pending_approvals?: number;
  };
}

export interface AdapterStat {
  adapter_id: string;
  name: string;
  adapter_type: string;
  protocol: string;
  is_online: boolean;
  total_assignments: number;
  success_count: number;
  failed_count: number;
  success_rate: number;
  avg_latency_ms: number | null;
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
  success_criteria?: CriteriaConfig;
  failure_criteria?: CriteriaConfig;
  verification_mode?: string;
  skill_id?: string | null;
  loop_config?: LoopConfig;
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
  items: TaskListItem[];
  total: number;
}

export interface TaskListItem extends Task {
  latest_run?: TaskRun | null;
}

export interface LoopConfig {
  max_iterations?: number;
  max_duration_seconds?: number;
  no_progress_threshold?: number | null;
  budget_limit?: number | null;
}

export interface RetryConfig {
  max_retries?: number;
  backoff_base_seconds?: number;
}

export interface CriteriaRule {
  type: string;
  path?: string;
  value?: unknown;
  values?: string[];
}

export interface CriteriaConfig {
  rules?: CriteriaRule[];
  match?: "all" | "any";
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  instructions: string;
  is_active: boolean;
}

export interface SkillCreate {
  name: string;
  description?: string;
  instructions?: string;
}

export interface SkillListResponse {
  items: Skill[];
  total: number;
}

export interface MemoryEntry {
  id: string;
  scope: string;
  scope_ref?: string | null;
  key: string;
  content: string;
  created_at: string;
}

export interface PendingApproval {
  id: string;
  workflow_run_id: string;
  workflow_id: string;
  workflow_name: string;
  run_status: string;
  node_id: string;
  title: string;
  message: string;
  status: string;
  created_at: string;
}

export interface WorkflowApproval {
  id: string;
  workflow_run_id: string;
  node_id: string;
  title: string;
  message: string;
  status: string;
  decided_by?: string | null;
  decision_note?: string | null;
  created_at: string;
  resolved_at?: string | null;
}

export interface TaskCreate {
  name: string;
  objective: string;
  agent_adapter_id?: string;
  priority?: number;
  sla_seconds?: number;
  tags?: string[];
  schedule_cron?: string | null;
  schedule_at?: string | null;
  loop_config?: LoopConfig;
  retry_config?: RetryConfig;
  success_criteria?: CriteriaConfig;
  failure_criteria?: CriteriaConfig;
  verification_mode?: string;
  skill_id?: string | null;
}

export interface RunLogs {
  run_id: string;
  logs: { timestamp: string; source: string; message: string; metadata: Record<string, unknown> }[];
}

export interface VerificationResult {
  id: string;
  run_id: string;
  iteration: number;
  verdict: string;
  reason: string;
  signals: Record<string, unknown>;
  verified_by: string;
  created_at: string;
}

export interface RunIteration {
  iteration: number;
  agent_status: string | null;
  result_payload: Record<string, unknown>;
  verification: VerificationResult | null;
  received_at: string | null;
}

export interface RunTimeline {
  run_id: string;
  task_id: string;
  objective: string;
  success_criteria: CriteriaConfig;
  verification_mode: string;
  status: string;
  iteration_count: number;
  max_iterations: number;
  budget_limit?: number | null;
  budget_usage?: { tokens?: number; cost?: number };
  long_term_memory?: { key: string; content: string; scope: string; metadata?: Record<string, unknown> }[];
  error_message: string | null;
  termination_reason: string | null;
  iterations: RunIteration[];
  events: { timestamp: string; source: string; message: string; metadata: Record<string, unknown> }[];
}

export interface Alert {
  id: string;
  severity: string;
  alert_type: string;
  content: string;
  run_id?: string | null;
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
  auth_config: Record<string, string>;
  status_mapping: Record<string, string>;
  is_online: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdapterCreate {
  name: string;
  adapter_type?: string;
  protocol?: "push" | "pull";
  endpoint: string;
  description?: string;
  auth_config?: Record<string, string>;
  status_mapping?: Record<string, string>;
  is_online?: boolean;
}

export interface AdapterUpdate extends Partial<AdapterCreate> {}

export interface AdapterHealth {
  adapter_id: string;
  status: "ok" | "error";
  adapter: string;
  protocol: string;
  is_online: boolean;
  assignment_count: number;
  latency_ms?: number;
  queue_depth?: number;
  pull_url?: string;
  endpoint_checked?: string;
  error?: string;
}

// --- MCP ---

export interface McpServer {
  id: string;
  name: string;
  mcp_type: string;
  transport: string;
  endpoint: string;
  description: string;
  auth_config: Record<string, string>;
  extra_config: Record<string, unknown>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface McpServerCreate {
  name: string;
  mcp_type?: string;
  transport?: "sse" | "http" | "stdio";
  endpoint: string;
  description?: string;
  auth_config?: Record<string, string>;
  extra_config?: Record<string, unknown>;
  is_enabled?: boolean;
}

export interface McpServerUpdate extends Partial<McpServerCreate> {}

export interface McpHealth {
  mcp_id: string;
  status: "Connected" | "Warning" | "Error" | "Disabled";
  latency_ms?: number;
  server_name?: string;
  server_version?: string;
  protocol_version?: string;
  tool_count?: number;
  resource_count?: number;
  error?: string;
}

// --- Workflow / Orchestrator ---

export type NodeType = "start" | "agent" | "end" | "condition" | "parallel" | "loop" | "approval";

export interface DagNode {
  id: string;
  type: NodeType;
  label: string;
  config: {
    trigger?: string;
    action?: string;
    adapter_id?: string;
    objective?: string;
    expression?: string;
    max_iterations?: number;
    title?: string;
    message?: string;
  };
  position: { x: number; y: number };
}

export interface DagEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface WorkflowDag {
  nodes: DagNode[];
  edges: DagEdge[];
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  dag: WorkflowDag;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowCreate {
  name: string;
  description?: string;
  dag?: WorkflowDag;
}

export interface WorkflowUpdate {
  name?: string;
  description?: string;
  dag?: WorkflowDag;
}

export interface WorkflowListResponse {
  items: Workflow[];
  total: number;
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  status: string;
  current_node_id: string | null;
  context: Record<string, unknown>;
  completed_nodes: string[];
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface WorkflowValidateResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface AiChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface AiOrchestratorRequest {
  message: string;
  history?: AiChatMessage[];
  current_dag?: WorkflowDag;
  adapter_names?: string[];
}

export interface AiOrchestratorResponse {
  reply: string;
  dag?: WorkflowDag;
  workflow_name?: string;
  suggestions?: string[];
}
