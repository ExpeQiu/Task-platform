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


class DashboardMetrics(BaseModel):
    total_tasks: int
    active_runs: int
    success_rate: float
    queue_backlog: int
    trend: list[dict]
    agent_distribution: list[dict]


class PullTaskResponse(BaseModel):
    assignment_id: UUID
    run_id: UUID
    task_id: str
    objective: str
    context: dict
    constraints: dict
    callback_url: str
