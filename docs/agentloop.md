# Agent Loop 技术深度研究报告

> **报告时间**：2026-06-10
> **研究级别**：深度研究
> **适用对象**：技术决策者、AI 架构师、开发者

---

## 一、核心概念：什么是 Agent Loop

### 1.1 定义

**Agent Loop（智能体循环）** 是指 AI Agent 在执行任务时，通过反复迭代"感知 → 推理 → 行动 → 反馈"这一闭环来完成任务的工作范式。与传统一次性响应的"请求-应答"模式不同，Agent Loop 赋予 AI **持续自主决策**的能力——在每个循环中，Agent 评估当前状态，决定下一步行动，执行后获取结果，再进入下一轮决策。

一个最简 Agent Loop 的本质是：

```
while not terminated:
    observation = perceive(state)
    action = plan(observation, memory)
    result = execute(action)
    state = update(state, result)
    memory = remember(state, result)
```

### 1.2 与传统自动化循环的本质区别

| 维度 | 传统自动化（RPA/脚本） | Agent Loop |
|------|----------------------|-----------|
| **决策方式** | 预设规则，条件分支 | LLM 动态推理 |
| **适应能力** | 固定流程，无法应对异常 | 可根据上下文自主调整 |
| **输入形式** | 结构化数据 | 自然语言、多模态 |
| **错误处理** | 依赖 try/catch 预定义 | 自主识别并恢复 |
| **流程定义** | 硬编码步骤 | 软编码（由 LLM 决定） |
| **泛化能力** | 仅限预设场景 | 可处理开放域任务 |
| **循环终止** | 固定次数/固定条件 | 动态判断（LLM 自身决定） |

### 1.3 Agent Loop 的核心价值

Agent Loop 将 AI 从**被动工具**转变为**主动代理**。其核心价值在于：

1. **长程任务分解**：将"写一份市场分析报告"这类模糊任务拆解为多步执行
2. **工具调用能力**：通过代码执行、API 调用、Web 搜索等工具拓展 LLM 能力边界
3. **自我纠错**：通过反思（reflection）识别错误并重新规划
4. **记忆积累**：跨轮次保持上下文，实现真正的"会话记忆"

---

## 二、技术架构：Agent Loop 的核心组件

一个完整的 Agent Loop 系统由以下六大组件构成：

### 2.1 感知（Perception）

负责将外部输入（用户指令、环境状态、历史交互）转化为 Agent 可理解的内部表示。

```
感知层职责：
├── 用户意图解析：将自然语言任务分解为可执行目标
├── 环境状态获取：获取工具返回结果、API 响应、文件内容等
├── 上下文管理：维护当前会话的上下文窗口
└── 多模态融合：整合文本、图像、代码执行结果等异构信息
```

### 2.2 规划（Planning）

Agent 的"大脑"，决定下一步做什么。规划能力直接决定 Agent 的任务完成质量。

```
规划层核心能力：
├── 任务分解（Task Decomposition）：将复杂任务拆解为子任务
├── 步骤排序（Step Sequencing）：确定子任务的执行顺序
├── 自我反思（Self-Reflection）：评估上一步结果，识别错误
├── 重规划（Re-planning）：当原计划失效时动态调整
└── 目标推理（Goal Reasoning）：理解最终目标与当前进展的关系
```

### 2.3 行动（Action）

Agent 与外部世界交互的接口。

```
行动类型：
├── 工具调用（Tool Use）：执行代码、查询数据库、调用 API、搜索网页
├── 信息检索（Retrieval）：从知识库、记忆系统中获取相关信息
├── 委托路由（Delegation）：将子任务交给其他 Agent 处理
├── 响应生成（Response）：向用户返回最终结果
└── 状态更新（State Update）：更新内部状态和记忆
```

### 2.4 记忆（Memory）

Agent 的"记忆系统"，分为三层：

```
记忆架构：
├── 短期记忆（Short-term）：当前会话的上下文窗口（Token 限制内）
│   └── 实现方式：滚动上下文、消息截断
├── 工作记忆（Working Memory）：当前任务的中间状态
│   └── 实现方式：变量绑定、状态对象、步骤记录
└── 长期记忆（Long-term）：跨会话积累的知识和经验
    └── 实现方式：向量数据库、键值存储、知识图谱
```

### 2.5 工具调用（Tool Use）

工具系统是 Agent Loop 区别于纯 LLM 推理的核心能力。

```
工具系统架构：
├── 工具定义（Tool Definition）：描述工具的名称、参数、返回值
├── 工具选择（Tool Selection）：根据当前任务选择合适的工具
├── 工具执行（Tool Execution）：调用工具并获取结果
├── 结果解析（Result Parsing）：将工具返回结果转化为 LLM 可理解的格式
└── 错误处理（Error Handling）：工具执行失败时的降级策略
```

### 2.6 循环控制（Loop Control）

决定何时继续、何时终止的核心机制。

```
控制机制：
├── 终止条件检测：评估当前状态是否满足任务完成条件
├── 最大迭代次数：防止无限循环（max_iterations）
├── Token 预算保护：当接近上下文上限时触发压缩或终止
├── 人类打断通道：允许用户随时干预停止循环
└── 收敛检测：通过指标判断是否进入无进展的"空转"状态
```

---

## 三、关键模式详解

### 3.1 ReAct（Reasoning + Acting）

**论文**：[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)（Yao et al., 2022，Google）

**核心思想**：将 LLM 的推理链（Thought）与具体行动（Action）交替进行，形成"边想边做"的模式。

**架构**：
```
用户输入 → Thought → Action → Observation → Thought → Action → ...
                   ↑                                      ↓
                   └──────────────────────────────────────┘
                          （循环直至终止）
```

**ReAct 的 Prompt 模板（经典版）**：
```
Task: {task}
Thought: {LLM 推理当前情况}
Action: {执行的行动，如 search[query], calculator[expr]}
Observation: {行动结果}
...（重复 Thought → Action → Observation）
Final Answer: {最终答案}
```

**ReAct 的优势**：
- 推理过程透明可追溯
- 错误可定位到具体步骤
- 在 HotpotQA、FALLC 等数据集上表现优异

**ReAct 的局限**：
- 对简单任务过于"昂贵"（每次行动都是一次 LLM 调用）
- 推理链长度受 Token 限制
- 无法处理需要并行行动的场景

**代码示例**：

```python
import json

def react_agent(task: str, tools: list, max_iterations: int = 10):
    """
    ReAct 循环的核心实现
    """
    observation = ""
    history = []
    
    for i in range(max_iterations):
        # Step 1: 构建 Prompt（包含历史 + 当前观察）
        prompt = build_react_prompt(task, history, observation)
        
        # Step 2: LLM 推理（Thinking）
        response = llm.generate(prompt)
        
        # Step 3: 解析 Action
        action_type, action_input = parse_action(response)
        
        if action_type == "Finish":
            return action_input  # 任务完成
        
        # Step 4: 执行工具
        if action_type in tools:
            observation = tools[action_type](action_input)
        else:
            observation = f"Unknown tool: {action_type}"
        
        # Step 5: 记录历史
        history.append({
            "thought": extract_thought(response),
            "action": f"{action_type}[{action_input}]",
            "observation": observation
        })
    
    return "Max iterations reached"

def build_react_prompt(task: str, history: list, observation: str) -> str:
    prompt = f"Task: {task}\n\n"
    for h in history:
        prompt += f"Thought: {h['thought']}\n"
        prompt += f"Action: {h['action']}\n"
        prompt += f"Observation: {h['observation']}\n"
    
    if observation:
        prompt += f"Observation: {observation}\n"
    
    prompt += "Thought: "
    return prompt
```

---

### 3.2 Plan-and-Execute（规划-执行分离）

**核心思想**：将任务分为"规划阶段"和"执行阶段"，先一次性生成完整计划，再按顺序执行。执行过程中若失败，可回到规划阶段重新规划。

**两种变体**：
1. **严格分离**（Strict Plan-and-Execute）：先规划，后执行，不交叉
2. **灵活分离**（Replan-enabled Execute）：执行中实时重规划

**架构对比**：

```
ReAct:         [思考→行动→观察] → [思考→行动→观察] → ...
                      ↑____________↓（单 Agent）

Plan-and-Exec: 规划Agent ──────────────────────────────────────→ 最终结果
                      ↓
              [子任务1] → [子任务2] → [子任务3] → ...
                      ↓
              执行Agent（逐个执行子任务，可并行）
```

**代码示例**：

```python
async def plan_and_execute(task: str, planner, executor):
    """
    Plan-and-Execute 模式
    """
    # Phase 1: 规划阶段 - Planner 生成完整计划
    plan = await planner.run(
        task=f"为以下任务制定执行计划：{task}\n"
             f"将任务分解为最小可执行的子任务，"
             f"每个子任务应可独立完成。"
    )
    
    subtasks = parse_plan(plan)  # 解析为子任务列表
    
    results = []
    for subtask in subtasks:
        # Phase 2: 执行阶段 - Executor 逐个执行子任务
        result = await executor.run(subtask)
        results.append(result)
        
        # Phase 3: 阶段性检查 - 评估是否需要重规划
        should_replan = await planner.evaluate(
            completed=results,
            remaining=subtasks[len(results):]
        )
        if should_replan:
            new_plan = await planner.replan(task, results)
            subtasks = parse_plan(new_plan)
    
    # Phase 4: 整合结果
    return await planner.synthesize(results)
```

**Plan-and-Execute 的优势**：
- 规划过程全局可见，便于人类审核
- 长任务的可控性更强
- 可在执行前预判资源消耗

**Plan-and-Execute 的局限**：
- 规划本身需要消耗大量 Token
- 规划阶段的错误会传播到整个执行
- 对动态变化的环境适应性不如 ReAct

---

### 3.3 Executive Agent / Supervisor Pattern（主管模式）

**核心思想**：引入一个"主管 Agent"（Supervisor/Orchestrator）负责协调多个专业 Worker Agent，主管只做任务分派和结果整合，不直接执行具体操作。

**架构**：
```
用户请求
    ↓
Supervisor Agent（主管）
    ├── 分析任务，决定需要哪些专业能力
    ├── 分派子任务给 Worker Agent
    │   ├── Worker A（研究能力）→ 搜集信息
    │   ├── Worker B（编码能力）→ 生成代码
    │   └── Worker C（写作能力）→ 撰写报告
    ├── 收集各 Worker 结果
    └── 整合输出最终答案
```

**代码示例**（多 Agent 协作）：

```python
# Microsoft AutoGen 风格的 Supervisor Pattern
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.tools import AgentTool

async def supervisor_team():
    # 定义专业 Worker Agent
    researcher = AssistantAgent(
        "researcher",
        system_message="你是一位专业研究员，负责搜集和分析信息。",
        tools=[search_tool, browse_tool]
    )
    
    coder = AssistantAgent(
        "coder",
        system_message="你是一位专业程序员，负责编写和调试代码。",
        tools=[code_executor_tool]
    )
    
    writer = AssistantAgent(
        "writer",
        system_message="你是一位专业写作助手，负责撰写清晰简洁的报告。"
    )
    
    # 主管 Agent
    supervisor = AssistantAgent(
        "supervisor",
        system_message="""你是一位项目主管。分析用户任务后，
        将任务分配给最合适的专员。
        专员包括：researcher（研究）、coder（编码）、writer（写作）。
        不要自己做具体工作，而是委托给专员完成。"""
    )
    
    # 创建 Agent Tool（将 Agent 本身作为工具暴露给其他 Agent）
    researcher_tool = AgentTool(researcher, return_value_as_last_message=True)
    coder_tool = AgentTool(coder, return_value_as_last_message=True)
    writer_tool = AgentTool(writer, return_value_as_last_message=True)
    
    # 为 Supervisor 装备其他 Agent 作为工具
    supervisor.tools = [researcher_tool, coder_tool, writer_tool]
    
    # 运行
    result = await supervisor.run(task="研究量子计算最新进展并撰写报告")
    return result
```

**Supervisor Pattern 的优势**：
- 模块化：每个 Worker 可独立开发、测试
- 可扩展：新增专业能力只需添加新 Worker
- 责任清晰：便于定位问题根因
- 支持并行：多个 Worker 可同时工作

**Supervisor Pattern 的局限**：
- 主管 Agent 的调度能力决定整体效率
- Agent 间通信引入额外延迟
- 需要设计良好的结果聚合机制

---

### 3.4 AutoGPT / BabyAGI 类自主循环

**代表项目**：
- [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT)：2023 年爆火的自主 Agent 项目
- [BabyAGI](https://github.com/yoheinakajima/babyagi)：基于任务驱动的自主 Agent 系统
- [AgentGPT](https://agentgpt.reworkd.ai/)：AutoGPT 的 Web UI 版本

**核心思想**：给定一个高层目标，Agent 自动分解任务、排列优先级、循环执行，直到目标达成。

**BabyAGI 的核心循环**：

```python
# BabyAGI 核心逻辑（简化版）
def babyagi(objective: str, initial_task: str):
    task_list = [initial_task]
    completed_tasks = []
    results = {}  # task_id -> result
    
    while task_list:
        # 1. 优先级排序
        task_list = prioritize_tasks(objective, task_list, completed_tasks)
        
        # 2. 取出最高优先级任务
        task = task_list.pop(0)
        
        # 3. 执行任务（LLM）
        result = execute_task(objective, task, results)
        
        # 4. 分析结果，生成新任务
        new_tasks = analyze_and_extend(objective, task, result)
        
        # 5. 添加新任务到队列
        for t in new_tasks:
            task_list.append(t)
        
        # 6. 记录完成
        completed_tasks.append(task)
        results[task.id] = result
    
    return results
```

**AutoGPT 的核心特性**：
1. **全自主**：用户只需给目标，Agent 自动完成全流程
2. **记忆持久化**：使用向量数据库存储历史交互
3. **自我批评**：Agent 会对自己的输出进行二次审查
4. **文件操作**：支持读写本地文件系统
5. **Web 访问**：集成浏览器进行网页搜索和内容提取

**AutoGPT 类系统的典型问题**：

| 问题 | 表现 | 根因 |
|------|------|------|
| **过早终止** | Agent 误判任务已完成 | 缺乏严格的完成标准 |
| **无限循环** | Agent 重复执行相同操作 | 缺乏去重和收敛检测 |
| **Token 爆炸** | 上下文快速膨胀 | 记忆管理不善 |
| **错误累积** | 早期错误导致全盘崩溃 | 缺乏检查点机制 |
| **资源浪费** | 大量无效 LLM 调用 | 规划能力不足 |

---

### 3.5 Multi-Agent 协作循环

**核心思想**：多个 Agent 形成协作网络，通过消息传递和角色分工共同完成复杂任务。

**常见协作拓扑**：

```
1. 层级式（Hierarchical）
       Supervisor
      /     |     \
   Worker  Worker  Worker

2. 并行式（Parallel）
   Worker ← User → Worker
       ↘     ↙
        Merger

3. 讨论式（Discussion）
   Agent A ↔ Agent B ↔ Agent C
        ↓         ↓
        └────↺────┘
          (循环讨论)

4. 市场式（Market）
   Task Queue ←→ Worker Pool
   (多个 Worker 竞争/协作接任务)
```

**代码示例**（CrewAI 风格的多 Agent 协作）：

```python
from crewai import Agent, Crew, Task, Process

# 定义专业 Agent
researcher = Agent(
    role="高级研究员",
    goal="准确、快速地搜集目标主题的深度信息",
    backstory="你是一位有10年经验的市场研究专家，擅长从公开信息中提炼关键洞察",
    tools=["search", "browse", "extract"]
)

analyst = Agent(
    role="战略分析师",
    goal="基于研究数据，提供有价值的战略建议",
    backstory="你是一位前麦肯锡顾问，擅长数据分析与战略咨询",
    tools=["analyze_data", "generate_charts"]
)

writer = Agent(
    role="商业报告撰写人",
    goal="将复杂分析转化为清晰、可执行的报告",
    backstory="你是一位资深商业作家，服务过数十家财富500强企业",
    tools=["write_report", "format_document"]
)

# 定义任务
research_task = Task(
    description="深入研究 AI Agent 市场现状，包括市场规模、主要玩家、技术趋势",
    agent=researcher,
    expected_output="结构化的市场研究报告"
)

analysis_task = Task(
    description="基于研究报告，进行SWOT分析，识别机会与风险",
    agent=analyst,
    expected_output="战略分析报告，包含SWOT矩阵和关键建议"
)

writing_task = Task(
    description="将研究员的报告和分析师的洞察整合为最终报告",
    agent=writer,
    expected_output="面向高管的可执行商业报告",
    context=[research_task, analysis_task]  # 依赖前两个任务
)

# 创建 Crew（团队）并执行
crew = Crew(
    agents=[researcher, analyst, writer],
    tasks=[research_task, analysis_task, writing_task],
    process=Process.sequential  # 顺序执行
)

result = crew.kickoff()
```

---

## 四、循环终止条件设计

循环终止是 Agent Loop 的核心控制机制，直接影响系统的**安全性**和**效率**。

### 4.1 终止条件类型

| 类型 | 描述 | 适用场景 |
|------|------|---------|
| **固定迭代次数** | `iterations >= max_iterations` | 通用保护，防止无限循环 |
| **任务完成** | LLM 判断或规则判断任务已达目标 | 正常流程终止 |
| **Token 耗尽** | 接近上下文窗口上限 | 资源保护 |
| **收敛停滞** | 多轮无实质性进展 | 防止空转 |
| **人类打断** | 用户主动停止 | 安全干预 |
| **错误超限** | 连续失败次数过多 | 容错保护 |
| **时间超限** | 执行时间超过阈值 | 实时系统要求 |

### 4.2 终止条件的工程实现

```python
from enum import Enum
from dataclasses import dataclass
from typing import Callable

class TerminationReason(Enum):
    MAX_ITERATIONS = "max_iterations"
    TASK_COMPLETED = "task_completed"
    TOKEN_LIMIT = "token_limit"
    CONVERGENCE = "convergence"
    HUMAN_INTERRUPT = "human_interrupt"
    ERROR_THRESHOLD = "error_threshold"
    TIMEOUT = "timeout"

@dataclass
class TerminationConfig:
    max_iterations: int = 50
    max_tokens_per_iteration: int = 4000
    convergence_threshold: int = 3  # 连续 N 轮无进展则终止
    max_errors: int = 5
    timeout_seconds: float = 300
    enable_human_interrupt: bool = True

class LoopController:
    def __init__(self, config: TerminationConfig):
        self.config = config
        self.iteration = 0
        self.error_count = 0
        self.convergence_count = 0
        self.last_meaningful_progress = ""
        self.start_time = None
    
    def should_terminate(
        self,
        current_result: str,
        total_tokens: int,
        human_stop: bool = False
    ) -> tuple[bool, TerminationReason]:
        self.iteration += 1
        
        # 人类打断
        if self.config.enable_human_interrupt and human_stop:
            return True, TerminationReason.HUMAN_INTERRUPT
        
        # 固定迭代次数
        if self.iteration >= self.config.max_iterations:
            return True, TerminationReason.MAX_ITERATIONS
        
        # Token 限制（保留 20% 余量）
        max_tokens = self.config.max_tokens_per_iteration * self.iteration
        context_limit = 120_000 * 0.8  # 假设 120k token 上下文
        if total_tokens > context_limit:
            return True, TerminationReason.TOKEN_LIMIT
        
        # 收敛检测：当前结果与上次相比无实质性变化
        if self._is_meaningful_change(current_result):
            self.convergence_count = 0
            self.last_meaningful_progress = current_result
        else:
            self.convergence_count += 1
        
        if self.convergence_count >= self.config.convergence_threshold:
            return True, TerminationReason.CONVERGENCE
        
        # 错误计数
        if self.error_count >= self.config.max_errors:
            return True, TerminationReason.ERROR_THRESHOLD
        
        # 超时
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > self.config.timeout_seconds:
                return True, TerminationReason.TIMEOUT
        
        return False, None
    
    def _is_meaningful_change(self, current: str) -> bool:
        if not self.last_meaningful_progress:
            return True
        # 简单的实质性变化检测
        return current.strip() != self.last_meaningful_progress.strip()
    
    def mark_error(self):
        self.error_count += 1
```

### 4.3 Token 限制下的长循环处理策略

当 Agent Loop 运行在长任务中时，Token 限制是最大的工程挑战。以下是主流策略：

**策略 1：上下文压缩（Context Compression）**

```python
async def compressed_loop(task: str, llm, tools: list):
    memory = []  # 原始历史
    context_window = []  # 当前使用的上下文
    
    MAX_CONTEXT = 60_000  # tokens
    
    for i in range(MAX_ITERATIONS):
        # 动态压缩历史
        if count_tokens(context_window) > MAX_CONTEXT * 0.7:
            summary = await llm.summarize("\n".join(memory))
            context_window = [summary] + context_window[-5:]  # 保留最近 5 轮
            memory = context_window.copy()
        
        response = await llm.generate(context_window)
        # ... 执行循环
```

**策略 2：阶段性快照（Checkpointing）**

```python
# 每 N 轮保存一次完整状态，支持从检查点恢复
class CheckpointManager:
    def save(self, iteration: int, state: dict):
        checkpoint = {
            "iteration": iteration,
            "task": state["task"],
            "subtasks": state["subtasks"],
            "memory": state["memory"],
            "context": state["context"]
        }
        with open(f"checkpoint_{iteration}.json", "w") as f:
            json.dump(checkpoint, f)
    
    def load(self, path: str) -> dict:
        with open(path) as f:
            return json.load(f)
```

**策略 3：层次化记忆（Hierarchical Memory）**

```
顶层：当前目标 + 最近 5 轮核心结果（始终保留）
中层：压缩后的历史摘要（每 10 轮压缩一次）
底层：完整历史（向量数据库，仅在需要时检索）
```

**策略 4：子任务分片（Task Chunking）**

将长任务分解为多个独立子任务，分别执行，最后合并结果。

---

## 五、工程挑战与解决方案

### 5.1 循环开销与性能

**问题**：每次循环都是一次 LLM API 调用，成本和延迟随迭代次数线性增长。

**解决方案**：

| 策略 | 原理 | 效果 |
|------|------|------|
| **快速失败** | 简单任务直接返回，避免循环 | 节省 80%+ LLM 调用 |
| **批量行动** | 单次 LLM 调用触发多个行动 | 减少循环次数 |
| **轻量级路由** | 用小模型做行动选择 | 降低单次成本 |
| **缓存复用** | 相同输入缓存 LLM 响应 | 避免重复计算 |
| **流式输出** | 边生成边执行，无需等待完整响应 | 降低感知延迟 |

**快速失败示例**：

```python
def quick_route(task: str) -> str:
    """
    在进入完整 Agent Loop 前，先用简单规则判断任务复杂度
    """
    simple_patterns = [
        r"^(你好|hi|hello|hey).*$",  # 问候
        r"^今天天气.*$",              # 简单查询
        r"^\d+\s*[+\-*/]\s*\d+$",    # 简单计算
    ]
    
    for pattern in simple_patterns:
        if re.match(pattern, task, re.IGNORECASE):
            return "direct_response"  # 不进入循环，直接回答
    
    return "agent_loop"  # 需要完整 Agent Loop
```

### 5.2 错误累积与恢复

**问题**：Agent 在中间步骤犯的错误会传播放大，导致最终结果完全错误。

**解决方案**：

1. **自我验证（Self-Verification）**：每个关键步骤后，让 Agent 验证自己的输出
2. **外部验证（External Verification）**：使用独立系统验证 Agent 输出
3. **检查点回滚（Checkpoint & Rollback）**：保存每个步骤的状态，出错时回滚
4. **多数投票（Majority Voting）**：同一任务执行多次，取多数结果

```python
class ErrorRecoveryAgent:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
    
    async def execute_with_recovery(self, task: str):
        for attempt in range(self.max_retries):
            try:
                result = await self.agent_loop(task)
                
                # 自我验证
                if await self.verify(result, task):
                    return result
                else:
                    # 验证失败，触发重试
                    task = await self.revise(task, result)
                    continue
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                # 回滚到上一个检查点
                await self.rollback()
    
    async def verify(self, result: str, task: str) -> bool:
        # 让 LLM 评估结果是否正确解决了任务
        prompt = f"验证以下结果是否正确解决了任务：\n任务：{task}\n结果：{result}\n如果正确回答 YES，不正确回答 NO。"
        response = await self.llm.generate(prompt)
        return "YES" in response.upper()
```

### 5.3 状态管理

**问题**：随着循环进行，状态（记忆、上下文、中间变量）管理复杂度指数上升。

**解决方案**：

```python
from dataclasses import dataclass, field
from typing import Any
import json

@dataclass
class AgentState:
    """Agent 循环的完整状态"""
    iteration: int = 0
    task: str = ""
    
    # 三层记忆
    short_term: list[dict] = field(default_factory=list)   # 当前会话消息
    working: dict[str, Any] = field(default_factory=dict)  # 工作状态
    long_term: list[dict] = field(default_factory=list)    # 长期记忆引用
    
    # 执行跟踪
    action_history: list[dict] = field(default_factory=list)
    tool_results: dict[str, Any] = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)
    
    # 检查点
    checkpoints: list[str] = field(default_factory=list)
    
    def save_checkpoint(self) -> str:
        """保存当前状态快照"""
        path = f"checkpoint_{self.iteration}.json"
        with open(path, "w") as f:
            json.dump({
                "iteration": self.iteration,
                "working": self.working,
                "action_history": self.action_history
            }, f)
        self.checkpoints.append(path)
        return path
    
    def rollback(self, checkpoint_path: str):
        """从检查点恢复"""
        with open(checkpoint_path) as f:
            data = json.load(f)
        self.iteration = data["iteration"]
        self.working = data["working"]
        self.action_history = data["action_history"]
```

### 5.4 并行 vs 串行循环

**串行循环**：每步等待前一步完成，再执行下一步
- 优点：简单、可控、易调试
- 缺点：效率低，无法利用并行性

**并行循环**：多个步骤同时执行
- 优点：效率高，适合独立子任务
- 缺点：状态管理复杂，依赖关系难处理

**混合策略**：关键路径串行，非关键路径并行

```python
async def parallel_agent_loop(task: str):
    """
    利用 asyncio 实现并行 Agent 循环
    """
    # Phase 1: 串行 - 理解任务和分解
    plan = await planner.analyze(task)
    subtasks = plan.subtasks
    
    # Phase 2: 并行执行独立子任务
    parallel_tasks = [t for t in subtasks if not t.has_dependencies]
    sequential_tasks = [t for t in subtasks if t.has_dependencies]
    
    async def execute_subtask(t):
        return await worker.execute(t)
    
    # 并行执行无依赖任务
    parallel_results = await asyncio.gather(
        *[execute_subtask(t) for t in parallel_tasks]
    )
    
    # Phase 3: 串行执行有依赖的任务
    sequential_results = []
    for t in sequential_tasks:
        result = await execute_subtask(t)
        sequential_results.append(result)
    
    # Phase 4: 串行 - 整合结果
    final_result = await aggregator.merge(parallel_results + sequential_results)
    return final_result
```

---

## 六、前沿进展（2024-2026）

### 6.1 微软 AutoGen → Microsoft Agent Framework (MAF)

**演进路径**：
- **AutoGen 0.2**（2023-2024）：多 Agent 编程框架，支持群聊、代码执行
- **AutoGen 进入维护模式**（2024）：官方宣布不再新增功能
- **Microsoft Agent Framework 1.0**（2025）：AutoGen 的生产级继承者

**MAF 核心特性**：
1. **多语言支持**：Python + C#/.NET API 一致
2. **A2A 协议**：Agent-to-Agent 通信协议标准化
3. **MCP 支持**：Model Context Protocol 原生集成
4. **工作流引擎**：图形化/代码化工作流定义（顺序、并行、交接、群聊）
5. **可观测性**：内置 OpenTelemetry 分布式追踪
6. **检查点与时间旅行**：支持暂停、恢复、历史回放
7. **Foundry 托管**：一行代码部署到 Azure Foundry

```python
# Microsoft Agent Framework 示例
from agent_framework import Agent, Workflow

# 定义工作流
workflow = Workflow("AIResearchTeam")
workflow.sequence(
    "researcher" → "analyst" → "writer"
)
workflow.add_gate("analyst", lambda r: r.quality_score > 0.8)

# 部署到 Foundry
await workflow.deploy_to_foundry()
```

### 6.2 LangChain / LangGraph

LangChain 从 2024 年起推出 `create_agent` API 和 LangGraph 持久化运行：

- **Deep Agents**：内置自动上下文压缩、虚拟文件系统、子 Agent 派生
- **持久化执行**：LangGraph 的 Checkpoint 机制支持任意时刻暂停和恢复
- **Human-in-the-loop**：`interrupt` 节点支持工作流暂停等待人类确认

### 6.3 CrewAI

CrewAI 定位为"生产就绪的多 Agent 平台"（2024-2026）：

- **Flows**：类似 LangGraph 的工作流编排引擎
- **Triggers**：支持 Gmail、Slack、Salesforce 等外部事件触发
- **企业特性**：RBAC 权限管理、生产环境监控
- **集成**：Amazon Bedrock Agents 直接集成

### 6.4 国产方案

| 方案 | 特点 | 定位 |
|------|------|------|
| **Coze（扣子）** | 字节跳动，拖拽式 Agent 构建平台 | 低代码 Agent 平台 |
| **Dify** | 开源 LLM 应用开发平台，支持工作流 | 开发者友好 |
| **AppGPT** | 国内团队，面向企业场景的 Agent 框架 | 企业应用 |
| **LangChain-Chatchat** | 基于 LangChain 的中文本地化 RAG+Agent | 知识库场景 |

### 6.5 关键标准协议

**MCP（Model Context Protocol）**：Anthropic 主导的 Agent 工具调用标准
- 类似 USB Type-C：统一接口连接 AI 模型与各种工具
- 已被 VS Code、Cursor、JetBrains 等 IDE 广泛采用

**A2A（Agent-to-Agent Protocol）**：Multi-Agent 通信协议
- Microsoft 主导，与 MCP 互补
- 支持 Agent 间的任务委派、状态同步、能力发现

---

## 七、代码示例：完整 Agent Loop 实现

### 7.1 最简 Agent Loop

```python
"""
最简 Agent Loop 实现
展示核心循环逻辑，不依赖任何外部框架
"""

import json
from dataclasses import dataclass
from typing import Optional

@dataclass
class Message:
    role: str
    content: str

class MinimalAgentLoop:
    def __init__(
        self,
        llm_client,
        tools: dict[str, callable],
        max_iterations: int = 20
    ):
        self.llm = llm_client
        self.tools = tools
        self.max_iterations = max_iterations
        self.messages: list[Message] = []
    
    def run(self, task: str) -> str:
        self.messages = [{
            "role": "system",
            "content": f"""你是一个任务执行助手。
你有以下工具可用：
{self._format_tools()}

对于每个步骤，先思考（Thought），然后选择工具执行（Action）。
当任务完成时，返回 Action: finish[最终答案]"""
        }]
        
        self.messages.append({"role": "user", "content": task})
        
        for _ in range(self.max_iterations):
            # 1. LLM 推理
            response = self.llm.chat(self.messages)
            self.messages.append({"role": "assistant", "content": response})
            
            # 2. 解析行动
            action_type, action_input = self._parse_action(response)
            
            # 3. 执行终止或行动
            if action_type == "finish":
                return action_input
            elif action_type in self.tools:
                result = self.tools[action_type](action_input)
                self.messages.append({
                    "role": "user",
                    "content": f"Observation: {result}"
                })
            else:
                self.messages.append({
                    "role": "user",
                    "content": f"Error: Unknown tool '{action_type}'"
                })
        
        return "Max iterations reached"
    
    def _format_tools(self) -> str:
        return "\n".join(
            f"- {name}: {tool.__doc__ or 'no description'}"
            for name, tool in self.tools.items()
        )
    
    def _parse_action(self, response: str) -> tuple[str, str]:
        # 简单的 Action 解析
        # 格式: Action: tool_name[input] 或 Action: finish[result]
        import re
        match = re.search(r"Action:\s*(\w+)\[(.*?)\]", response, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return "unknown", ""
```

### 7.2 带有记忆管理的 Agent Loop

```python
"""
带完整记忆管理的 Agent Loop
展示三层记忆（短期、工作、长期）的实现
"""

class MemoryManagedAgentLoop:
    def __init__(self, llm_client, vector_store, config: dict):
        self.llm = llm_client
        self.vector_store = vector_store  # 长期记忆（向量数据库）
        self.config = config
        
        # 短期记忆：当前消息历史
        self.short_term: list[dict] = []
        
        # 工作记忆：当前任务状态
        self.working_memory: dict = {
            "task": "",
            "subtasks": [],
            "completed_steps": [],
            "accumulated_knowledge": {}
        }
        
        # Token 预算管理
        self.total_tokens = 0
        self.max_tokens = config.get("max_tokens", 100_000)
        self.compression_threshold = config.get("compression_threshold", 0.7)
    
    async def run(self, task: str) -> str:
        self.working_memory["task"] = task
        
        # 1. 检查长期记忆是否有相关上下文
        relevant_history = await self.vector_store.search(
            query=task,
            top_k=5
        )
        
        # 2. 构建初始上下文
        system_prompt = self._build_system_prompt(relevant_history)
        self.short_term = [{"role": "system", "content": system_prompt}]
        self.short_term.append({"role": "user", "content": task})
        
        # 3. 主循环
        for iteration in range(self.config["max_iterations"]):
            
            # 3a. Token 预算检查
            if self._should_compress():
                await self._compress_context()
            
            # 3b. LLM 生成
            response = await self.llm.generate(self.short_term)
            self.short_term.append({"role": "assistant", "content": response})
            self.total_tokens += self._count_tokens(response)
            
            # 3c. 解析并执行
            action = self._parse_llm_response(response)
            
            if action["type"] == "finish":
                await self._save_to_long_term_memory(task, action["result"])
                return action["result"]
            
            elif action["type"] == "tool":
                result = await self._execute_tool(action["name"], action["input"])
                self.short_term.append({
                    "role": "user",
                    "content": f"Tool Result: {result}"
                })
                self.working_memory["completed_steps"].append({
                    "action": action,
                    "result": result,
                    "iteration": iteration
                })
            
            elif action["type"] == "replan":
                new_plan = action["plan"]
                self.working_memory["subtasks"] = new_plan
        
        return "Task incomplete: max iterations reached"
    
    async def _compress_context(self):
        """上下文压缩：将历史消息压缩为摘要"""
        # 用 LLM 生成摘要
        history_text = "\n".join(
            f"{m['role']}: {m['content'][:200]}"
            for m in self.short_term[1:]  # 跳过 system prompt
        )
        
        summary_prompt = (
            f"将以下对话历史压缩为简短摘要，保留关键信息：\n{history_text}"
        )
        summary = await self.llm.generate([
            {"role": "user", "content": summary_prompt}
        ])
        
        # 替换为压缩后的版本
        self.short_term = [self.short_term[0]]  # 保留 system prompt
        self.short_term.append({
            "role": "system",
            "content": f"[历史摘要] {summary}"
        })
    
    async def _save_to_long_term_memory(self, task: str, result: str):
        """将结果存入长期记忆"""
        await self.vector_store.add(
            text=f"Task: {task}\nResult: {result}",
            metadata={"task_type": "agent_loop_result"}
        )
```

---

## 八、总结与建议

### 8.1 技术成熟度评估

| 模式 | 成熟度 | 推荐场景 | 风险提示 |
|------|--------|---------|---------|
| ReAct | ★★★★★ 生产级 | 需要推理透明性的任务 | 长链推理 Token 消耗大 |
| Plan-and-Execute | ★★★★☆ 生产级 | 复杂长程任务 | 规划开销需优化 |
| Supervisor Pattern | ★★★★☆ 生产级 | 多专业协作场景 | 主管 Agent 能力瓶颈 |
| AutoGPT 类 | ★★★☆☆ 实验级 | POC/快速原型 | 需严格控制终止条件 |
| Multi-Agent 协作 | ★★★☆☆ 发展中 | 开放域复杂任务 | 通信开销和状态一致性 |

### 8.2 技术选型建议

| 需求 | 推荐方案 |
|------|---------|
| 快速构建单 Agent | LangChain `create_agent` / CrewAI |
| 多 Agent 协作 | Microsoft Agent Framework / AutoGen |
| 生产级多 Agent | Microsoft Agent Framework 1.0 |
| 本地部署 | LangChain + Ollama / LlamaIndex |
| 低代码平台 | Coze / Dify |
| 企业级管控 | Microsoft MAF + Azure Foundry |

### 8.3 核心工程关注点

1. **循环终止是安全底线** — 永远设置 `max_iterations`，并结合收敛检测
2. **Token 管理是成本关键** — 从设计阶段就规划上下文压缩策略
3. **状态持久化是可靠性保障** — 检查点机制让系统可恢复
4. **工具是 Agent 的能力边界** — 精心设计工具定义和错误处理
5. **人类在环是信任基础** — 关键决策点保留人工确认通道

---

## 参考资源

### 核心论文
- [ReAct: Synergizing Reasoning and Acting in Language Models (2022)](https://arxiv.org/abs/2210.03629)
- [PlanBench: A Benchmark for Planning Capabilities of Language Models (2023)](https://arxiv.org/abs/2306.17100)
- [Generative Agents: Interactive Simulacra of Human Behavior (2023)](https://arxiv.org/abs/2304.03442)
- [AutoGen: Enabling Next-Gen AI Applications via Multi-Agent Conversation (2023)](https://arxiv.org/abs/2308.00352)

### 框架与工具
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) — 生产级多 Agent 框架
- [AutoGen](https://github.com/microsoft/autogen) — 微软多 Agent 框架（维护模式）
- [LangChain / LangGraph](https://python.langchain.com) — Agent 开发平台
- [CrewAI](https://github.com/crewAIInc/crewAI) — 多 Agent 协作平台
- [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) — 自主 Agent 参考实现
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io) — 工具调用标准

### 协议标准
- [A2A (Agent-to-Agent Protocol)](https://learn.microsoft.com/en-us/agent-framework/reference/a2a/overview) — Agent 间通信协议
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io) — Anthropic 主导的工具标准

---

*本报告由 AI-Researcher 生成，参考截至 2026-06 的公开信息。*
*报告版本：v1.0 | 2026-06-10*
