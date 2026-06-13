# Phase 2 Loop 增强说明

在 Phase 1 闭环（Goal / Verifier / LoopGuard / 可视化）基础上，本阶段扩展五项能力。

## 1. 独立 LLM Verifier Agent

- `verification_mode`: `rule_based`（默认）| `llm_agent` | `hybrid`
- `llm_agent`: 仅由独立 LLM 验证器裁决，与执行 Agent 分离
- `hybrid`: 规则验证通过后再由 LLM 二次确认
- Mock 模式：`AI_MOCK_MODE=true` 时使用 `llm_agent_mock`，不消耗 Token

## 2. 工作流人工审批节点

- DAG 节点类型新增 `approval`
- 节点 config: `title`, `message`
- 流程运行到审批节点时状态变为 `PendingApproval`
- API:
  - `GET /v1/workflows/runs/{run_id}/approvals`
  - `POST /v1/workflows/runs/{run_id}/approvals/{approval_id}/decide`

## 3. Skill / Playbook 资产化

- 表 `skills`: name, instructions, input/output contract
- API: `/v1/skills` CRUD
- 创建任务时可选 `skill_id`，自动将 instructions 注入 objective

## 4. budget_limit 执行

- Agent 回调 `result_payload` 中提供 `tokens_used` 或 `token_usage`
- 累计至 `TaskRun.context.budget_usage`
- 超过 `loop_config.budget_limit` 时触发 `BudgetExceeded` 告警并终止

## 5. 长期记忆

- 表 `memory_entries`: scope (`global` / `task_type` / `task`), key, content
- API: `POST/GET /v1/memory`
- 任务 dispatch 时自动注入 `long_term_memory` 到 run.context
- 任务成功时自动沉淀简要经验
