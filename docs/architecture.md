# AI 公司系统架构设计 v2.0

## 概述

本系统是一个多层级的 AI 智能体架构，模拟一个自我进化的"AI 公司"。系统采用分层治理模式，具备：
- **元认知能力**：上帝层观察系统运行，推动自我进化
- **决策能力**：C-Suite 高管团队协作决策
- **执行能力**：动态 Agent 池并行执行任务
- **学习能力**：从任务中积累知识，持续进化

---

## 系统全景图

```
┌─────────────────────────────────────────────────────────────────┐
│                          上帝层                                  │
│                     (Meta-cognition)                            │
│                                                                 │
│   观察系统运行 → 发现模式 → 识别知识缺口 → 触发学习 → 推动进化    │
│                                                                 │
│   触发：每周定时 + 每 N 个任务后                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 观察 / 进化指令
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         决策层                                   │
│                      (C-Suite)                                  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   CEO    │  │   COO    │  │   CHRO   │  │   CFO    │        │
│  │  决策者   │  │  协调者   │  │  招聘官   │  │  财务官   │        │
│  │          │  │          │  │          │  │ (可选)   │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │             │               │
│       └─────────────┴──────┬──────┴─────────────┘               │
│                            │                                    │
│                    ┌───────▼───────┐                            │
│                    │    顾问团      │                            │
│                    │  (思维框架)    │                            │
│                    └───────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ COO 协调分配
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         执行层                                   │
│                    (Execution Layer)                            │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                  Agent 并行协作池                        │    │
│  │   ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐          │    │
│  │   │Agent A│  │Agent B│  │Agent C│  │Agent D│   ...    │    │
│  │   └───┬───┘  └───┬───┘  └───┬───┘  └───┬───┘          │    │
│  │       └──────────┴─────┬────┴──────────┘              │    │
│  │                        ▼                              │    │
│  │                   并行执行                             │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │     MCP      │  │    Skills    │  │    Tools     │          │
│  │  (外部能力)   │  │  (可复用流程) │  │  (内部工具)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                    Hooks 系统                          │    │
│  │   PreTask → Executing → PostTask → OnError → Done     │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        共享知识库                                │
│                    (Knowledge Base)                             │
│                                                                 │
│              向量检索 + 持久化存储 + 全层共享                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 一、上帝层 (God Layer)

### 定位
系统的**元认知层**，不参与具体任务执行，专注于观察、分析和推动进化。

### 核心职责
| 职责 | 说明 |
|-----|------|
| 观察 | 监控任务执行模式、成功率、知识使用情况 |
| 分析 | 识别知识缺口、发现系统瓶颈 |
| 进化 | 触发自动学习、优化知识库 |
| 报告 | 生成进化周报、提供改进建议 |

### 触发机制
| 类型 | 条件 | 说明 |
|-----|------|-----|
| 定时触发 | 每周一次 | 全面分析系统运行状况 |
| 事件触发 | 每完成 N 个任务 | 快速检查，发现即时问题 |
| 手动触发 | 用户请求 | 按需运行进化 |

### 权限边界

**可以自动执行：**
- 分析任务完成情况，生成统计报告
- 发现知识缺口，记录学习建议
- 有限度自动学习（每周最多 N 条新知识）
- 整理和优化知识库标签

**不能做：**
- 删除已有知识（只能标记过时）
- 修改核心系统配置
- 超出学习配额的操作

### 接口定义
```python
class GodLayer:
    """上帝层 - 元认知与自我进化"""

    # 观察能力
    def observe_task_patterns(self) -> TaskAnalysis
    def identify_knowledge_gaps(self) -> list[KnowledgeGap]

    # 进化能力
    def auto_learn(self, max_items: int) -> list[Knowledge]
    async def run_evolution(self, trigger_type: TriggerType) -> EvolutionLog

    # 报告能力
    def generate_weekly_report(self) -> EvolutionReport
    def get_status(self) -> dict
```

---

## 二、决策层 (C-Suite)

### 定位
系统的**管理层**，由多个高管角色协作完成任务理解、决策和资源调度。

### 角色分工

#### 2.1 CEO - 首席执行官
**职责**：理解用户意图，做出战略决策

```python
class CEO:
    """首席执行官 - 理解与决策"""

    async def understand_task(self, user_input: str) -> Task:
        """理解用户意图，转化为结构化任务"""

    async def consult_advisors(self, task: Task) -> list[Opinion]:
        """咨询顾问团获取多元视角"""

    async def make_decision(self, task: Task, opinions: list) -> Decision:
        """综合信息做出决策"""

    async def delegate(self, decision: Decision) -> None:
        """将任务委派给 COO 执行"""
```

#### 2.2 COO - 首席运营官
**职责**：协调执行层，监督任务进度，确保交付

```python
class COO:
    """首席运营官 - 协调与监督"""

    async def plan_execution(self, decision: Decision) -> ExecutionPlan:
        """将决策拆解为执行计划"""

    async def coordinate_agents(self, plan: ExecutionPlan) -> None:
        """协调 Agent 并行执行"""

    async def monitor_progress(self, task_id: str) -> Progress:
        """监控执行进度"""

    async def aggregate_results(self, results: list) -> FinalResult:
        """汇总执行结果，向 CEO 汇报"""
```

#### 2.3 CHRO - 首席人力资源官
**职责**：管理 Agent 池，按需分配执行者

```python
class CHRO:
    """首席人力资源官 - Agent 管理"""

    # Agent 能力注册表
    agent_registry: dict[str, AgentProfile]

    def register_agent(self, agent_type: str, profile: AgentProfile):
        """注册新的 Agent 类型"""

    async def hire_for_task(self, requirements: list[str]) -> list[Agent]:
        """根据任务需求招聘合适的 Agent"""

    def evaluate_performance(self, agent: Agent, result: TaskResult):
        """评估 Agent 表现，反馈给上帝层"""

    def get_available_agents(self) -> list[AgentProfile]:
        """获取可用 Agent 列表"""
```

#### 2.4 CFO - 首席财务官 (可选)
**职责**：管理资源预算，控制 Token 成本

```python
class CFO:
    """首席财务官 - 资源管理"""

    daily_budget: int  # 每日 Token 预算
    spending_log: list[SpendingRecord]

    async def approve_budget(self, task: Task) -> tuple[bool, str]:
        """审批任务预算"""

    def track_spending(self, task_id: str, tokens_used: int):
        """追踪支出"""

    def get_cost_report(self) -> CostReport:
        """生成成本报告"""

    def get_remaining_budget(self) -> int:
        """获取剩余预算"""
```

### 顾问团 (Advisory)

**定位**：思维框架，非固定人设。被 CEO 咨询时提供多元视角。

#### 6 个基础视角
| 视角 | 关注点 | 典型问题 |
|-----|-------|---------|
| **战略视角** (strategic) | 长期方向、竞争格局、资源配置 | "这对长期有什么影响？" |
| **产品视角** (product) | 用户需求、功能优先级、体验 | "用户真正需要什么？" |
| **技术视角** (technical) | 可行性、架构、性能、安全 | "技术上怎么实现最优？" |
| **用户视角** (user) | 行为动机、心理、体验感受 | "用户会怎么想/怎么做？" |
| **商业视角** (business) | 成本、收益、商业模式 | "这能赚钱吗？怎么赚？" |
| **风险视角** (risk) | 潜在问题、法规、安全 | "有什么风险？" |

#### 接口定义
```python
class AdvisorySystem:
    """顾问系统 - 多元视角建议"""

    async def get_perspective(
        self,
        perspective: Perspective,
        context: str
    ) -> AdvisorOpinion:
        """获取特定视角的建议"""

    async def consult(
        self,
        context: str,
        perspectives: list[Perspective] = None  # None = 自动选择
    ) -> list[AdvisorOpinion]:
        """咨询多个视角"""

    async def synthesize(
        self,
        opinions: list[AdvisorOpinion]
    ) -> str:
        """综合多个视角的意见"""
```

---

## 三、执行层 (Execution Layer)

### 定位
系统的**工作层**，由动态组建的 Agent 团队完成具体任务。

### 3.1 Agent 并行协作池

```python
class AgentPool:
    """Agent 池 - 管理和调度执行 Agent"""

    agents: dict[str, Agent]

    async def execute_parallel(self, subtasks: list[SubTask]) -> list[Result]:
        """并行执行多个子任务"""
        results = await asyncio.gather(*[
            self.get_agent(task.agent_type).execute(task)
            for task in subtasks
        ])
        return results

    async def execute_sequential(self, subtasks: list[SubTask]) -> list[Result]:
        """顺序执行（有依赖关系时）"""

    def get_agent(self, agent_type: str) -> Agent:
        """获取或创建 Agent 实例"""
```

### 3.2 预置 Agent 类型

| Agent 类型 | 能力描述 | 适用场景 |
|-----------|---------|---------|
| `researcher` | 搜索和调研 | 竞品分析、市场调研 |
| `analyst` | 数据分析 | 数据解读、趋势分析 |
| `writer` | 文案撰写 | 报告生成、内容创作 |
| `engineer` | 技术实现 | 代码编写、技术方案 |
| `designer` | 设计相关 | UI/UX、视觉设计 |
| `reviewer` | 审核校验 | 质量检查、合规审核 |

### 3.3 MCP (外部能力)

```yaml
# 预置 MCP
mcp_registry:
  search:
    provider: "exa"
    description: "网页搜索"
  docs:
    provider: "context7"
    description: "官方文档查询"
  code:
    provider: "grep_app"
    description: "GitHub 代码搜索"
  # 可扩展...
```

### 3.4 Skills (可复用流程)

```python
class Skill:
    """可复用的任务流程"""
    name: str
    description: str
    required_agents: list[str]
    steps: list[SkillStep]

# 预置 Skills
skill_registry = {
    "competitive_analysis": CompetitiveAnalysisSkill(),
    "user_research": UserResearchSkill(),
    "technical_review": TechnicalReviewSkill(),
    "content_creation": ContentCreationSkill(),
}
```

### 3.5 Hooks 系统

```python
class HookManager:
    """钩子管理器 - 在关键节点插入自定义逻辑"""

    hooks = {
        "pre_task": [],       # 任务开始前
        "post_task": [],      # 任务完成后
        "pre_tool_use": [],   # 工具调用前
        "post_tool_use": [],  # 工具调用后
        "on_error": [],       # 出错时
        "on_progress": [],    # 进度更新时
    }

    def register(self, hook_name: str, callback: Callable):
        """注册钩子"""

    async def trigger(self, hook_name: str, context: dict):
        """触发钩子"""
```

---

## 四、记忆系统

系统采用分层记忆架构，不同层级使用不同类型的记忆。

### 记忆分层

```
┌─────────────────────────────────────────────────────┐
│                    上帝层记忆                        │
│                  (Evolution Log)                    │
│                                                     │
│  内容：观察记录、模式发现、学习决策、进化日志          │
│  特点：只追加、用于自省和复盘                        │
│  存储：evolution_log.json                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                   决策层记忆                         │
│                 (Working Memory)                    │
│                                                     │
│  内容：当前任务上下文、对话历史、临时状态              │
│  特点：短期、会话级别、任务完成后可清理               │
│  存储：内存 / Redis（如需持久化）                    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                    共享知识库                        │
│                 (Knowledge Base)                    │
│                                                     │
│  内容：长期知识、经验、方法论、最佳实践               │
│  特点：持久化、向量检索、全层共享                    │
│  存储：ChromaDB + JSON 元数据                       │
└─────────────────────────────────────────────────────┘
```

### 知识类型

```python
class KnowledgeType(str, Enum):
    # 方法论（怎么做）
    METHODOLOGY = "methodology"
    BEST_PRACTICE = "best_practice"

    # 洞察（为什么）
    INSIGHT = "insight"
    THINKING_PATTERN = "thinking_pattern"

    # 经验（做过什么）
    PROJECT_EXPERIENCE = "project_experience"
    CASE_STUDY = "case_study"

    # 参考（外部知识）
    DOCUMENTATION = "documentation"
    EXTERNAL_KNOWLEDGE = "external_knowledge"
```

---

## 五、数据流

### 5.1 任务处理流程

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ CEO: 理解任务                                        │
│      ├── 咨询顾问团 ← 获取多元视角                   │
│      ├── 检索知识库 ← 获取相关知识                   │
│      └── 做出决策                                    │
└─────────────────────────────────────────────────────┘
    │
    │ 委派给 COO
    ▼
┌─────────────────────────────────────────────────────┐
│ COO: 规划执行                                        │
│      ├── 拆分子任务                                  │
│      ├── 向 CHRO 申请 Agent                          │
│      └── (可选) 向 CFO 申请预算                       │
└─────────────────────────────────────────────────────┘
    │
    │ 协调 Agent
    ▼
┌─────────────────────────────────────────────────────┐
│ 执行层: 并行执行                                     │
│      ├── Agent A ──┐                                │
│      ├── Agent B ──┼── 并行工作                      │
│      └── Agent C ──┘                                │
│                │                                    │
│                ▼                                    │
│      ├── 使用 MCP (外部工具)                         │
│      ├── 调用 Skills (复用流程)                      │
│      └── 触发 Hooks (扩展点)                         │
└─────────────────────────────────────────────────────┘
    │
    │ 汇总结果
    ▼
┌─────────────────────────────────────────────────────┐
│ COO → CEO: 汇报结果                                  │
│ CEO: 审核 → 返回给用户                               │
└─────────────────────────────────────────────────────┘
    │
    │ 记录
    ▼
┌─────────────────────────────────────────────────────┐
│ 任务日志 → 上帝层观察                                │
└─────────────────────────────────────────────────────┘
```

### 5.2 进化流程

```
上帝层
   │
   ├──观察──→ 任务日志
   │            │
   │            ▼
   │         模式分析
   │            │
   │            ▼
   ├──发现──→ 知识缺口
   │            │
   │            ▼
   ├──学习──→ 新知识 ──→ 共享知识库
   │
   └──报告──→ 进化周报 ──→ 用户
```

---

## 六、安全边界

### 上帝层限制
| 限制项 | 默认值 | 说明 |
|-------|-------|-----|
| 每周自动学习上限 | 10 条 | 防止 token 消耗失控 |
| 单次学习冷却 | 1 小时 | 避免频繁触发 |
| 知识删除 | 禁止 | 只能标记过时，不能删除 |
| 配置修改 | 禁止 | 核心配置需人工修改 |

### 决策层限制
| 限制项 | 默认值 | 说明 |
|-------|-------|-----|
| 单任务最大 token | 可配置 | 防止单任务消耗过大 |
| 并行 Agent 数量 | 5 | 控制并发资源 |

### CFO 预算控制 (可选)
| 限制项 | 默认值 | 说明 |
|-------|-------|-----|
| 每日 token 预算 | 可配置 | 超出则拒绝新任务 |
| 单任务预算上限 | 可配置 | 大任务需要审批 |

---

## 七、配置示例

```yaml
# config/system.yaml

# ==================== 上帝层配置 ====================
god_layer:
  schedule:
    weekly_day: "sunday"
    weekly_hour: 3
  event_trigger:
    task_count: 20
  limits:
    max_weekly_learning: 10
    learning_cooldown_hours: 1

# ==================== 决策层配置 ====================
c_suite:
  ceo:
    default_perspectives:
      - strategic
      - product
      - technical
  coo:
    max_parallel_agents: 5
    timeout_seconds: 300
  chro:
    agent_pool_size: 10
  cfo:
    enabled: false  # 可选开启
    daily_budget: 100000  # tokens

# ==================== 顾问团配置 ====================
advisory:
  available_perspectives:
    - strategic
    - product
    - technical
    - user
    - business
    - risk
  auto_select_count: 3

# ==================== 执行层配置 ====================
execution:
  agent_types:
    - researcher
    - analyst
    - writer
    - engineer
    - designer
    - reviewer

  mcp:
    search:
      provider: "exa"
      api_key_env: "EXA_API_KEY"
    docs:
      provider: "context7"
    code:
      provider: "grep_app"

  hooks:
    enabled: true

  # 多模型策略（省钱）
  model_routing:
    coordinator: "claude-opus-4"      # 复杂决策用强模型
    researcher: "claude-sonnet-4"     # 搜索用中等模型
    writer: "claude-haiku"            # 写作用便宜模型

# ==================== 知识库配置 ====================
knowledge_base:
  embedding_type: "local"
  store_type: "chroma"
  data_dir: "data/knowledge"
  search:
    default_top_k: 5
    min_score: 0.3
```

---

## 八、与现有代码的映射

| 现有文件 | 新架构定位 | 改动 |
|---------|----------|-----|
| `src/agents/god_layer.py` | 上帝层 | 保留，增强 |
| `src/agents/ceo_agent.py` | CEO | 拆分决策和执行 |
| `src/agents/advisory.py` | 顾问团 | 保留 |
| `src/memory/knowledge_base.py` | 共享知识库 | 保留 |
| `src/memory/store.py` | 工作记忆 | 简化 |
| - | COO | **新增** |
| - | CHRO | **新增** |
| - | CFO | **新增（可选）** |
| - | AgentPool | **新增** |
| - | HookManager | **新增** |

---

## 九、下一步实现计划

1. [ ] 实现 COO 协调层
2. [ ] 实现 CHRO Agent 管理
3. [ ] 实现 Agent 并行协作池
4. [ ] 添加 Hooks 系统
5. [ ] 集成 MCP 外部能力
6. [ ] 实现 Skills 可复用流程
7. [ ] (可选) 实现 CFO 预算控制
8. [ ] 编写集成测试
9. [ ] 性能优化和成本控制
