from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoopConfig(BaseModel):
    max_iterations: int = 10
    max_duration_seconds: int = 3600
    no_progress_threshold: int | None = None
    budget_limit: int | None = None


class RetryConfig(BaseModel):
    max_retries: int = 3
    backoff_base_seconds: int = 30


class TaskCreate(BaseModel):
    name: str
    objective: str
    priority: int = 5
    sla_seconds: int = 300
    tags: list[str] = Field(default_factory=list)
    agent_adapter_id: UUID | None = None
    schedule_cron: str | None = None
    schedule_at: datetime | None = None
    loop_config: LoopConfig = Field(default_factory=LoopConfig)
    retry_config: RetryConfig = Field(default_factory=RetryConfig)


class TaskUpdate(BaseModel):
    name: str | None = None
    objective: str | None = None
    priority: int | None = None
    sla_seconds: int | None = None
    tags: list[str] | None = None
    agent_adapter_id: UUID | None = None
    schedule_cron: str | None = None
    schedule_at: datetime | None = None
    loop_config: LoopConfig | None = None
    retry_config: RetryConfig | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    objective: str
    priority: int
    sla_seconds: int
    tags: list
    agent_adapter_id: UUID | None
    schedule_cron: str | None
    schedule_at: datetime | None
    loop_config: dict
    retry_config: dict
    status: str
    created_at: datetime
    updated_at: datetime


class TaskRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    status: str
    version: int
    iteration_count: int
    retry_count: int
    context: dict
    progress: int
    started_at: datetime | None
    last_updated_at: datetime
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime


class TaskDetailResponse(TaskResponse):
    latest_run: TaskRunResponse | None = None


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int


class AgentFeedbackWebhook(BaseModel):
    run_id: UUID
    feedback_id: str | None = None
    status: str
    result_payload: dict[str, Any] = Field(default_factory=dict)
    logs: list[Any] = Field(default_factory=list)
    error_code: str | None = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    severity: str
    alert_type: str
    content: str
    run_id: UUID | None
    status: str
    created_at: datetime
    resolved_at: datetime | None


class AlertUpdate(BaseModel):
    status: str


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor: str
    action: str
    target: str
    detail: str
    metadata_json: dict
    created_at: datetime


class AdapterCreate(BaseModel):
    name: str
    adapter_type: str = "generic"
    protocol: str = "push"
    endpoint: str
    description: str = ""
    auth_config: dict = Field(default_factory=dict)
    status_mapping: dict = Field(default_factory=dict)
    is_online: bool = True


class AdapterUpdate(BaseModel):
    name: str | None = None
    adapter_type: str | None = None
    protocol: str | None = None
    endpoint: str | None = None
    description: str | None = None
    auth_config: dict | None = None
    status_mapping: dict | None = None
    is_online: bool | None = None


class AdapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    adapter_type: str
    protocol: str
    endpoint: str
    description: str
    auth_config: dict
    status_mapping: dict
    is_online: bool
    created_at: datetime
    updated_at: datetime


class RunLogEntry(BaseModel):
    timestamp: datetime
    source: str
    message: str
    metadata: dict = Field(default_factory=dict)


class RunLogsResponse(BaseModel):
    run_id: UUID
    logs: list[RunLogEntry]


class AdapterStat(BaseModel):
    adapter_id: str
    name: str
    adapter_type: str
    protocol: str
    is_online: bool
    total_assignments: int
    success_count: int
    failed_count: int
    success_rate: float
    avg_latency_ms: float | None = None


class DashboardMetrics(BaseModel):
    total_tasks: int
    active_runs: int
    success_rate: float
    queue_backlog: int
    trend: list[dict]
    agent_distribution: list[dict]
    adapter_stats: list[AdapterStat] = Field(default_factory=list)


class PullTaskResponse(BaseModel):
    assignment_id: UUID
    run_id: UUID
    task_id: str
    objective: str
    context: dict
    constraints: dict
    callback_url: str


# --- Workflow / Orchestrator ---

VALID_NODE_TYPES = {"start", "agent", "end", "condition", "parallel", "loop"}


class DagNodePosition(BaseModel):
    x: float = 0
    y: float = 0


class DagNodeConfig(BaseModel):
    trigger: str | None = None
    adapter_id: UUID | None = None
    adapter_name: str | None = None
    objective: str | None = None
    expression: str | None = None
    max_iterations: int | None = None
    action: str | None = None


class DagNode(BaseModel):
    id: str
    type: str
    label: str
    config: DagNodeConfig = Field(default_factory=DagNodeConfig)
    position: DagNodePosition = Field(default_factory=DagNodePosition)


class DagEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None


class WorkflowDag(BaseModel):
    nodes: list[DagNode] = Field(default_factory=list)
    edges: list[DagEdge] = Field(default_factory=list)


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    dag: WorkflowDag = Field(default_factory=WorkflowDag)


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    dag: WorkflowDag | None = None


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    dag: dict
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(BaseModel):
    items: list[WorkflowResponse]
    total: int


class WorkflowRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    status: str
    current_node_id: str | None
    context: dict
    completed_nodes: list
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class WorkflowRunTrigger(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)


class WorkflowValidateResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AiChatMessage(BaseModel):
    role: str
    content: str


class AiOrchestratorRequest(BaseModel):
    message: str
    history: list[AiChatMessage] = Field(default_factory=list)
    current_dag: WorkflowDag | None = None
    adapter_names: list[str] = Field(default_factory=list)


class AiOrchestratorResponse(BaseModel):
    reply: str
    dag: WorkflowDag | None = None
    workflow_name: str | None = None
    suggestions: list[str] = Field(default_factory=list)


# --- MCP ---

MCP_TYPES = {"RAG", "Skill", "Memory", "Custom"}
MCP_TRANSPORTS = {"sse", "http", "stdio"}


class McpServerCreate(BaseModel):
    name: str
    mcp_type: str = "Custom"
    transport: str = "sse"
    endpoint: str
    description: str = ""
    auth_config: dict = Field(default_factory=dict)
    extra_config: dict = Field(default_factory=dict)
    is_enabled: bool = True


class McpServerUpdate(BaseModel):
    name: str | None = None
    mcp_type: str | None = None
    transport: str | None = None
    endpoint: str | None = None
    description: str | None = None
    auth_config: dict | None = None
    extra_config: dict | None = None
    is_enabled: bool | None = None


class McpServerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    mcp_type: str
    transport: str
    endpoint: str
    description: str
    auth_config: dict
    extra_config: dict
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class McpHealthResult(BaseModel):
    mcp_id: str
    status: str  # Connected | Warning | Error | Disabled
    latency_ms: float | None = None
    server_name: str | None = None
    server_version: str | None = None
    protocol_version: str | None = None
    tool_count: int | None = None
    resource_count: int | None = None
    error: str | None = None
