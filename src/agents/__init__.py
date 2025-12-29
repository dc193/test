"""AI 公司智能体系统

三层架构：
- 上帝层 (God Layer): 元认知与进化
- C-Suite 决策层: CEO (决策)、COO (协调)、CHRO (Agent管理)
- 执行层: AgentPool、ExecutionAgent、Hooks、ContextManager

设计哲学：
- 灵魂 (Soul): 本项目原创架构 - 回答 WHAT & WHY
- 身体 (Body): 借鉴 Oh My OpenCode 实践 - 回答 HOW
"""

# 上帝层
from .god_layer import GodLayer, TriggerType, TaskRecord

# 顾问系统
from .advisory import AdvisorySystem, Perspective, PERSPECTIVE_PROFILES

# C-Suite 决策层
from .ceo_agent import CEOAgent, Task, TaskResult
from .coo import COO, ExecutionPlan, ExecutionResult, SubTask, ExecutionProgress
from .chro import CHRO, AgentProfile, AgentCapability, PerformanceRecord

# 执行层
from .execution_agent import ExecutionAgent, ExecutionContext
from .agent_pool import AgentPool, AgentInstance, AgentStatus, PoolStats
from .hooks import HookManager, HookType, HookDefinition, HookRegistry, hook
from .context_manager import ContextManager, ContextWindow, CompressionStrategy, TokenUsage

__all__ = [
    # 上帝层
    "GodLayer",
    "TriggerType",
    "TaskRecord",

    # 顾问系统
    "AdvisorySystem",
    "Perspective",
    "PERSPECTIVE_PROFILES",

    # C-Suite
    "CEOAgent",
    "Task",
    "TaskResult",
    "COO",
    "ExecutionPlan",
    "ExecutionResult",
    "SubTask",
    "ExecutionProgress",
    "CHRO",
    "AgentProfile",
    "AgentCapability",
    "PerformanceRecord",

    # 执行层
    "ExecutionAgent",
    "ExecutionContext",
    "AgentPool",
    "AgentInstance",
    "AgentStatus",
    "PoolStats",
    "HookManager",
    "HookType",
    "HookDefinition",
    "HookRegistry",
    "hook",
    "ContextManager",
    "ContextWindow",
    "CompressionStrategy",
    "TokenUsage",
]
