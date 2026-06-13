# Task Platform 中的 Loop 设计说明

## 1. 文档目的

本文档不再从外部产品能力出发介绍 Loop，而是结合当前仓库实现，说明 Task Platform 如何作为一个面向多 Agent 执行的 Loop 控制平面来设计、落地和演进。

Task Platform 当前已经具备以下基础能力：

- 统一任务模型与状态机
- 基于 Celery 的调度与重试
- 工作流 DAG 编排
- Push / Pull 两种 Agent 接入协议
- MCP Server 管理与探测
- 告警、审计、指标与基础观测

因此，本文档的核心问题不是“Loop 是什么”，而是“本项目如何把 Agent Loop 工程化”。

## 2. 平台定位

### 2.1 角色定义

在本项目中，Task Platform 的定位应当是：

**Agent Loop 的控制平面（Control Plane），而不是单个 Agent 的执行体。**

平台本身不负责替代 Agent 内部的推理过程，而是负责以下事情：

- 定义目标和任务边界
- 生成或承载执行计划
- 调度 Agent 执行每一轮动作
- 接收反馈并推进状态流转
- 判断是否继续下一轮，或者终止
- 对异常、超时、空转和失败进行治理
- 记录全链路审计信息

换句话说，Agent 负责“做事”，平台负责“让事情持续、可控地做下去”。

### 2.2 本项目中的 Loop 定义

在 Task Platform 中，一个 Loop 可以定义为：

> 围绕某个业务目标，由平台持续调度一个或多个 Agent 执行，接收反馈，完成校验，并在满足终止条件前持续推进的闭环执行过程。

其最小闭环为：

```text
Goal -> Plan -> Dispatch -> Feedback -> Verify -> Continue or Stop
```

如果扩展为平台级闭环，则还应包含：

```text
Goal -> Plan -> Dispatch -> Feedback -> Verify -> State Transition
     -> Audit / Alert / Retry / Timeout Scan -> Continue or Stop
```

## 3. 当前仓库与 Loop 的对应关系

从现有实现看，仓库已经具备 Loop 的核心骨架。

### 3.1 调度与时钟

Loop 必须有持续推进能力，而不能依赖人工手动触发。当前仓库中已有两类关键机制：

- `scheduler.py` 负责处理定时任务和入队触发
- `watchdog.py` 负责扫描超时执行并触发治理动作

这意味着平台已经具备 Loop 的“时钟”和“巡检器”。

### 3.2 任务状态流转

Loop 的本质不是一次调用，而是一连串可追踪的状态推进。当前项目中：

- `Task` 表示任务模板
- `TaskRun` 表示一次具体执行实例
- `Feedback` 表示 Agent 回传结果
- `StateMachineService` 负责状态转移约束
- `TaskService` 负责提交、回调、失败、重试和再次分发

这套模型天然适合承载单任务 Loop。

### 3.3 多步计划与多 Agent 协作

复杂 Loop 不会只包含单一动作，还会出现并行、分支、循环和结束节点。当前项目中：

- `WorkflowEngine` 已支持 `start`、`agent`、`condition`、`parallel`、`loop`、`end` 等节点类型
- `ai_orchestrator.py` 可以把自然语言意图转换成 DAG

这说明平台已经具备从“单任务执行”走向“目标驱动的多步 Loop 编排”的能力基础。

### 3.4 连接器与外部能力

Loop 不能只停留在本地文件或纯对话层，必须接入真实外部系统。当前项目中：

- `mcp.py` 提供 MCP Server 的管理接口
- `mcp_client.py` 提供连通性探测能力

因此，平台已经具备作为 Connector Hub 的雏形。

### 3.5 治理能力

生产级 Loop 的关键不只是执行，还包括防失控。当前项目中已有：

- Loop 次数与时长限制
- 失败告警
- 超时扫描
- 审计日志记录

其中 `loop_guard.py` 已经承担平台级兜底裁决器的角色。

## 4. 目标设计原则

如果要让本项目真正支持 Loop，第一原则不是先增加更多 Agent，而是先把目标定义清楚。

### 4.1 目标必须可验证

一个可执行的 Loop 目标，必须能被平台或独立验证器判断是否完成，而不能只依赖 Agent 自报完成。

例如：

- 错误目标：完成登录模块优化
- 更好的目标：`test/auth` 下测试全部通过，`lint` 通过，且未引入新的高优先级告警

因此，本项目中的 Goal 不应只是自然语言描述，而应至少拆成两部分：

- `objective`: 业务目标
- `success_criteria`: 完成标准

### 4.2 目标必须可终止

任何 Loop 都必须配套显式终止条件。当前项目已经有 `max_iterations` 和 `max_duration_seconds`，但从设计上建议扩展为以下几类：

- 达成目标终止
- 达到最大迭代次数终止
- 达到最大执行时长终止
- 连续无进展终止
- 连续错误超限终止
- 人工终止

### 4.3 目标必须有治理边界

平台层要始终是最高仲裁者。Agent 可以申请继续下一轮，但是否允许继续，应由平台判断。

## 5. 推荐的 Loop 运行时模型

结合当前实现，推荐将 Task Platform 的 Loop 运行时拆成六个核心模块。

### 5.1 Goal Engine

职责：

- 接收用户输入的业务目标
- 解析并保存验收条件
- 生成可执行的任务或工作流定义

当前仓库中，可由以下部分承接：

- `Task` 的 `objective`
- `Task.loop_config`
- 未来新增的 `success_criteria`
- AI 编排入口 `ai_orchestrator.py`

### 5.2 Planner

职责：

- 把高层目标拆解为执行计划
- 决定是单任务执行还是工作流执行
- 生成串行、并行、条件分支或循环节点

当前仓库中，对应能力为：

- `ai_orchestrator.py` 的自然语言转 DAG
- `WorkflowDefinition` 和 `WorkflowEngine`

建议后续把 Planner 明确分为两层：

- 规则型 Planner：基于模板或配置生成 DAG
- AI Planner：用模型生成初始流程草案

### 5.3 Loop Runtime

职责：

- 创建执行实例
- 投递任务到目标 Agent
- 接收反馈并推进状态
- 决定是否发起下一轮

当前仓库中，对应实现主要集中在：

- `TaskService.submit_task`
- `TaskService.dispatch_run`
- `TaskService.handle_feedback`
- Celery 任务分发链路

这是当前项目里最接近 Loop 核心引擎的部分。

### 5.4 Verifier

职责：

- 判断当前结果是否满足完成条件
- 判断是否需要继续下一轮
- 判断是否进入失败、停滞或人工介入状态

这一层是当前项目相对欠缺的能力。现阶段更多是依据 Agent 回调状态直接推进成功或失败，但严格来说这还不是“独立验证”。

建议按阶段演进：

- MVP：规则验证器
  - 根据状态码、日志关键字、结构化结果字段判断
  - 根据测试是否通过、产物是否存在等规则判断
- Phase 2：Agent Verifier
  - 引入独立的验证 Agent，不与执行 Agent 共用指令
- Phase 3：混合验证器
  - 规则校验 + 独立 Agent 评审 + 人工确认节点

### 5.5 Memory

职责：

- 保存当前任务执行状态
- 保存中间结果
- 支持跨轮次复用上下文
- 为后续相似任务提供经验沉淀

当前仓库中已有两类基础记忆：

- 运行态记忆：`TaskRun.context`、`WorkflowRun.context`
- 过程记忆：`Feedback`、`AuditEvent`

但从长期设计看，建议把 Memory 拆成三层：

- 短期记忆：本轮最近上下文和最新反馈
- 工作记忆：当前任务变量、中间产物、当前节点结果
- 长期记忆：跨任务复用的经验、模板、常见失败模式、Skill 说明

### 5.6 Connector Hub

职责：

- 对接 MCP Server
- 对接外部知识、数据库、工单系统、通知系统
- 给 Agent 提供可执行的真实世界动作入口

当前项目已有 MCP 管理与探测，可作为统一连接器入口。后续建议继续扩展：

- 工具元数据管理
- 权限边界与审计
- 按任务或租户进行连接器路由

## 6. 当前实现中的关键设计判断

### 6.1 单任务 Loop 与工作流 Loop 应并存

本项目不应只支持一种 Loop 形态，而应支持两种运行模式：

#### 模式一：单任务 Loop

适合：

- 单 Agent 反复执行直到满足条件
- 基础抓取、分析、修复、生成类任务

实现载体：

- `Task`
- `TaskRun`
- `loop_config`
- `TaskService`

#### 模式二：工作流 Loop

适合：

- 多 Agent 协作
- 串行和并行混合
- 带条件判断和局部重试
- 需要明确节点级控制的复杂流程

实现载体：

- `WorkflowDefinition`
- `WorkflowRun`
- `WorkflowEngine`

设计上建议把两者统一为：

> 单任务 Loop 是最小执行单元，工作流 Loop 是多个执行单元的组合。

### 6.2 平台必须保留最终裁决权

无论 Agent 回调声称 `success`、`failed` 还是 `requires_action`，平台都不能完全信任单次回调。

正确的设计应是：

- Agent 回调只代表“本轮执行结果”
- 平台验证器决定“目标是否完成”
- 状态机决定“是否进入下一轮”

这能避免 Agent 自评过高导致的伪成功。

### 6.3 LoopGuard 应从简单兜底扩展为收敛治理器

当前 `loop_guard.py` 已经具备以下能力：

- 最大迭代次数限制
- 最大执行时长限制

后续建议扩展为更完整的收敛治理器，增加：

- 无进展检测
- 重复输出检测
- 错误密度检测
- Token 或成本预算限制

### 6.4 审计和告警不是附属功能，而是 Loop 基础设施

Loop 的一个核心特征是“持续执行且可能失控”，因此：

- 审计用于回答每一轮为什么继续、为什么停止
- 告警用于在异常时把问题及时抛给人

这也是当前项目区别于简单 Agent Demo 的重要价值点。

## 7. 建议补齐的数据模型

为了让 Loop 的设计更完整，建议在现有数据模型基础上增加以下概念。

### 7.1 Goal

建议引入显式 Goal 概念，或在 `Task` 中补充以下字段：

- `objective`: 目标描述
- `success_criteria`: 成功标准
- `failure_criteria`: 失败判据
- `approval_policy`: 是否要求人工确认

### 7.2 VerificationResult

用于记录每轮验证结果，建议包含：

- `run_id`
- `iteration`
- `verdict`
- `reason`
- `signals`
- `verified_by`

### 7.3 ProgressSnapshot

用于支撑无进展检测和收敛分析，建议包含：

- `run_id`
- `iteration`
- `summary`
- `artifacts`
- `delta_score`

### 7.4 Skill 或 Playbook

如果后续要支持跨任务复用意图，建议显式建模：

- `name`
- `description`
- `instructions`
- `applicable_task_types`
- `input_contract`
- `output_contract`

这类对象不一定一开始就要做成插件系统，但至少应成为平台内可复用资产。

## 8. 分阶段落地建议

### 8.1 Phase 1: 以现有代码为基础完成 MVP 闭环

目标：把现有“任务编排平台”升级为“基础 Loop 平台”。

建议优先做：

1. 在任务模型中补充 `success_criteria`
2. 增加规则型 Verifier
3. 让 `handle_feedback` 不再直接把 Agent `success` 等同于任务完成
4. 增加无进展检测
5. 在前端展示每轮迭代信息和终止原因

这一阶段不追求复杂智能，而是先让 Loop 可解释、可终止、可追踪。

### 8.2 Phase 2: 增强多 Agent 与验证能力

建议增加：

- 独立 Verifier Agent
- 工作流级条件路由增强
- 子任务级重试策略
- 人工审批节点
- 更强的 Memory 抽象

### 8.3 Phase 3: 扩展为企业级 Loop 控制平面

建议增加：

- Skill Registry
- 长期记忆与经验沉淀
- 连接器权限治理
- 多租户隔离
- 成本与 Token 预算控制
- 沙箱 / Worktree / 执行隔离

## 9. 与原始 Loop 概念的关系

外部产品强调的自动化调度、Skill、连接器、子 Agent、记忆，本质上在本项目里都可以找到对应落点，但表达方式需要转换：

- 自动化调度 -> Celery Scheduler + Watchdog
- 子 Agent 协作 -> Workflow Engine + 多 Agent 节点
- Connector -> MCP Hub
- 记忆 -> Context + Feedback + Audit + Long-term Memory
- Skill -> 平台级可复用任务模板 / Playbook / Prompt Asset

因此，本项目不需要照搬某个 Agent 产品的交互形式，而应坚持平台视角：

> 平台负责治理闭环，Agent 负责完成局部动作，Verifier 负责判断是否收敛到目标。

## 10. 结论

Task Platform 当前已经不是一个简单的异步任务中心，而是一个具备 Loop 雏形的多 Agent 编排与治理平台。

从设计上，下一步最关键的不是继续堆更多 Agent 类型，而是补齐以下三个核心能力：

1. 显式 Goal 与 Success Criteria
2. 独立 Verifier 机制
3. 更完善的收敛检测与长期记忆

当这三部分补齐后，Task Platform 才能从“支持 Agent 执行”真正升级为“支持目标持续推进直到完成的 Loop 平台”。

## 11. 数据契约

第一版 Loop 闭环的数据契约见 [loop-contracts.md](./loop-contracts.md)，包括：

- `success_criteria` / `failure_criteria` JSON 结构
- Verifier 输出枚举（`passed` / `failed` / `needs_continue`）
- 状态流：`Agent success → Reviewing → Verify → Success | Iterating | Failed`
- 旧任务兼容策略（无 criteria 时 Agent success 即 passed）
