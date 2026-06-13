# Loop 契约说明

本文档冻结 Task Platform Loop 闭环第一版的数据契约，供前后端与 Verifier 对齐。

## Task 新增字段

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `success_criteria` | JSONB | `{}` | 成功完成标准 |
| `failure_criteria` | JSONB | `{}` | 失败判据（可选） |
| `verification_mode` | string | `rule_based` | `rule_based` / `llm_agent` / `hybrid` |

## success_criteria / failure_criteria 结构

```json
{
  "rules": [
    { "type": "field_equals", "path": "tests_passed", "value": true },
    { "type": "field_exists", "path": "report_url" }
  ],
  "match": "all"
}
```

- `match`: `all`（全部满足）或 `any`（任一满足）
- `rules`: 规则数组，见下文

## 规则类型（第一版）

| type | 参数 | 说明 |
|------|------|------|
| `field_exists` | `path` | `result_payload` 中存在该路径字段 |
| `field_equals` | `path`, `value` | 字段值等于指定值 |
| `field_not_exists` | `path` | 字段不存在 |
| `status_in` | `values` | Agent 回调 status 在列表中 |

路径使用点分法，如 `summary.tests_passed`。

## Verifier 输出

| verdict | 含义 |
|---------|------|
| `passed` | 平台判定目标已完成 |
| `failed` | 平台判定失败 |
| `needs_continue` | 需继续下一轮迭代 |

## 兼容策略

当 `success_criteria` 与 `failure_criteria` 均为空（无 rules 或 rules 为空）时：

- Agent 回调 `success` → Verifier 短路返回 `passed`
- 保持与旧版「Agent success 即任务成功」一致

## 状态流

```text
Agent success → Reviewing → Verify
  → passed → Success
  → needs_continue → Iterating → dispatch_run → Running
  → failed → Failed

Agent requires_action → Reviewing → Verify (或直接进入 needs_continue)
```

## VerificationResult 记录

每轮验证写入 `verification_results` 表：

- `run_id`, `iteration`, `verdict`, `reason`, `signals`, `verified_by`

## 无进展检测

`loop_config.no_progress_threshold` 为 null 时跳过检测。

连续 N 轮 `result_payload` JSON 完全一致时触发 `NoProgressDetected` 告警并终止。
