"""CHRO (首席人力资源官) - Agent 管理

职责：
- 管理 Agent 能力注册表
- 根据任务需求招聘合适的 Agent
- 评估 Agent 表现
- 向上帝层反馈 Agent 使用情况
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Any
from enum import Enum
import json
from pathlib import Path


class AgentCapability(str, Enum):
    """Agent 能力类型"""
    RESEARCH = "research"        # 搜索调研
    ANALYSIS = "analysis"        # 数据分析
    WRITING = "writing"          # 文案撰写
    ENGINEERING = "engineering"  # 技术实现
    DESIGN = "design"            # 设计相关
    REVIEW = "review"            # 审核校验
    GENERAL = "general"          # 通用


@dataclass
class AgentProfile:
    """Agent 档案"""
    agent_type: str
    name: str
    description: str
    capabilities: list[AgentCapability]
    model: str = "default"  # 使用的模型
    cost_level: int = 1     # 成本级别 1-3，越高越贵
    performance_score: float = 0.5  # 表现评分 0-1
    total_tasks: int = 0
    successful_tasks: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    def to_dict(self) -> dict:
        return {
            "agent_type": self.agent_type,
            "name": self.name,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "model": self.model,
            "cost_level": self.cost_level,
            "performance_score": self.performance_score,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentProfile":
        data["capabilities"] = [AgentCapability(c) for c in data.get("capabilities", [])]
        return cls(**data)


@dataclass
class PerformanceRecord:
    """表现记录"""
    agent_type: str
    task_id: str
    task_description: str
    success: bool
    duration_seconds: float
    quality_score: Optional[float] = None  # 0-1，可选的质量评分
    recorded_at: str = field(default_factory=lambda: datetime.now().isoformat())


# 预置 Agent 档案
DEFAULT_AGENT_PROFILES = {
    "researcher": AgentProfile(
        agent_type="researcher",
        name="调研员",
        description="擅长搜索信息、收集资料、整理调研报告",
        capabilities=[AgentCapability.RESEARCH],
        model="sonnet",
        cost_level=2
    ),
    "analyst": AgentProfile(
        agent_type="analyst",
        name="分析师",
        description="擅长数据分析、趋势解读、洞察提取",
        capabilities=[AgentCapability.ANALYSIS],
        model="sonnet",
        cost_level=2
    ),
    "writer": AgentProfile(
        agent_type="writer",
        name="文案",
        description="擅长撰写文档、报告、内容创作",
        capabilities=[AgentCapability.WRITING],
        model="haiku",
        cost_level=1
    ),
    "engineer": AgentProfile(
        agent_type="engineer",
        name="工程师",
        description="擅长代码编写、技术方案设计、问题排查",
        capabilities=[AgentCapability.ENGINEERING],
        model="sonnet",
        cost_level=2
    ),
    "designer": AgentProfile(
        agent_type="designer",
        name="设计师",
        description="擅长 UI/UX 设计、视觉设计、用户体验优化",
        capabilities=[AgentCapability.DESIGN],
        model="sonnet",
        cost_level=2
    ),
    "reviewer": AgentProfile(
        agent_type="reviewer",
        name="审核员",
        description="擅长质量检查、合规审核、内容校验",
        capabilities=[AgentCapability.REVIEW],
        model="haiku",
        cost_level=1
    ),
    "general": AgentProfile(
        agent_type="general",
        name="通用助手",
        description="通用任务处理",
        capabilities=[AgentCapability.GENERAL],
        model="sonnet",
        cost_level=2
    ),
}


class CHRO:
    """首席人力资源官 - Agent 管理"""

    def __init__(
        self,
        agent_pool=None,
        data_dir: str = "data/chro",
        llm_provider=None
    ):
        self.agent_pool = agent_pool
        self.llm = llm_provider
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Agent 注册表
        self._registry: dict[str, AgentProfile] = {}
        self._performance_log: list[PerformanceRecord] = []

        # 数据文件
        self._registry_file = self.data_dir / "agent_registry.json"
        self._performance_file = self.data_dir / "performance_log.json"

        # 加载数据
        self._load_data()

        # 初始化默认 Agent
        self._init_default_agents()

    def _load_data(self):
        """加载数据"""
        if self._registry_file.exists():
            try:
                with open(self._registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._registry = {
                        k: AgentProfile.from_dict(v) for k, v in data.items()
                    }
            except Exception as e:
                print(f"加载 Agent 注册表失败: {e}")

        if self._performance_file.exists():
            try:
                with open(self._performance_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._performance_log = [
                        PerformanceRecord(**r) for r in data
                    ]
            except Exception as e:
                print(f"加载表现记录失败: {e}")

    def _save_registry(self):
        """保存注册表"""
        with open(self._registry_file, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.to_dict() for k, v in self._registry.items()},
                f, ensure_ascii=False, indent=2
            )

    def _save_performance(self):
        """保存表现记录"""
        # 只保留最近 1000 条
        recent = self._performance_log[-1000:]
        with open(self._performance_file, "w", encoding="utf-8") as f:
            json.dump(
                [{"agent_type": r.agent_type, "task_id": r.task_id,
                  "task_description": r.task_description, "success": r.success,
                  "duration_seconds": r.duration_seconds,
                  "quality_score": r.quality_score, "recorded_at": r.recorded_at}
                 for r in recent],
                f, ensure_ascii=False, indent=2
            )

    def _init_default_agents(self):
        """初始化默认 Agent"""
        for agent_type, profile in DEFAULT_AGENT_PROFILES.items():
            if agent_type not in self._registry:
                self._registry[agent_type] = profile
        self._save_registry()

    def register_agent(self, profile: AgentProfile):
        """注册新的 Agent 类型"""
        self._registry[profile.agent_type] = profile
        self._save_registry()
        print(f"Agent 已注册: {profile.agent_type} ({profile.name})")

    def unregister_agent(self, agent_type: str):
        """注销 Agent"""
        if agent_type in self._registry:
            del self._registry[agent_type]
            self._save_registry()

    async def hire_for_task(
        self,
        requirements: list[str],
        budget_level: int = 3,
        prefer_high_performance: bool = True
    ) -> list:
        """根据任务需求招聘合适的 Agent

        Args:
            requirements: 需要的 Agent 类型列表
            budget_level: 预算级别 1-3
            prefer_high_performance: 是否优先选择高表现 Agent

        Returns:
            Agent 实例列表
        """
        hired = []

        for req in requirements:
            # 查找匹配的 Agent
            agent_type = self._match_agent_type(req)

            if agent_type and agent_type in self._registry:
                profile = self._registry[agent_type]

                # 检查预算
                if profile.cost_level > budget_level:
                    # 尝试找更便宜的替代
                    agent_type = self._find_cheaper_alternative(agent_type, budget_level)
                    if agent_type:
                        profile = self._registry[agent_type]
                    else:
                        continue

                # 创建 Agent 实例
                if self.agent_pool:
                    agent = self.agent_pool.get_agent(agent_type)
                else:
                    agent = self._create_agent_instance(profile)

                hired.append(agent)

        return hired

    def _match_agent_type(self, requirement: str) -> Optional[str]:
        """匹配 Agent 类型"""
        req_lower = requirement.lower()

        # 直接匹配
        if req_lower in self._registry:
            return req_lower

        # 关键词匹配
        keyword_map = {
            "researcher": ["研究", "调研", "搜索", "查找", "research", "search"],
            "analyst": ["分析", "数据", "统计", "analyze", "data"],
            "writer": ["写", "撰写", "文案", "内容", "write", "content"],
            "engineer": ["开发", "代码", "技术", "实现", "code", "engineer"],
            "designer": ["设计", "UI", "UX", "界面", "design"],
            "reviewer": ["审核", "检查", "校验", "review", "check"],
        }

        for agent_type, keywords in keyword_map.items():
            if any(kw in req_lower for kw in keywords):
                return agent_type

        return "general"

    def _find_cheaper_alternative(self, agent_type: str, max_cost: int) -> Optional[str]:
        """查找更便宜的替代 Agent"""
        original = self._registry.get(agent_type)
        if not original:
            return None

        # 找同能力但更便宜的
        for at, profile in self._registry.items():
            if (profile.cost_level <= max_cost and
                any(c in profile.capabilities for c in original.capabilities)):
                return at

        return None

    def _create_agent_instance(self, profile: AgentProfile):
        """创建 Agent 实例"""
        from .execution_agent import ExecutionAgent
        return ExecutionAgent(
            agent_type=profile.agent_type,
            profile=profile,
            llm_provider=self.llm
        )

    def evaluate_performance(
        self,
        agent_type: str,
        task_id: str,
        task_description: str,
        success: bool,
        duration_seconds: float,
        quality_score: float = None
    ):
        """评估 Agent 表现"""
        # 记录表现
        record = PerformanceRecord(
            agent_type=agent_type,
            task_id=task_id,
            task_description=task_description,
            success=success,
            duration_seconds=duration_seconds,
            quality_score=quality_score
        )
        self._performance_log.append(record)
        self._save_performance()

        # 更新 Agent 档案
        if agent_type in self._registry:
            profile = self._registry[agent_type]
            profile.total_tasks += 1
            if success:
                profile.successful_tasks += 1

            # 更新表现评分（滑动平均）
            new_score = 1.0 if success else 0.0
            if quality_score is not None:
                new_score = (new_score + quality_score) / 2
            profile.performance_score = (
                profile.performance_score * 0.9 + new_score * 0.1
            )

            self._save_registry()

    def get_available_agents(self) -> list[AgentProfile]:
        """获取可用 Agent 列表"""
        return list(self._registry.values())

    def get_agent_profile(self, agent_type: str) -> Optional[AgentProfile]:
        """获取 Agent 档案"""
        return self._registry.get(agent_type)

    def get_top_performers(self, limit: int = 5) -> list[AgentProfile]:
        """获取表现最好的 Agent"""
        agents = list(self._registry.values())
        agents.sort(key=lambda a: (a.performance_score, a.success_rate), reverse=True)
        return agents[:limit]

    def get_performance_stats(self) -> dict:
        """获取表现统计"""
        if not self._performance_log:
            return {"total_tasks": 0}

        total = len(self._performance_log)
        successful = len([r for r in self._performance_log if r.success])

        by_agent = {}
        for record in self._performance_log:
            if record.agent_type not in by_agent:
                by_agent[record.agent_type] = {"total": 0, "success": 0}
            by_agent[record.agent_type]["total"] += 1
            if record.success:
                by_agent[record.agent_type]["success"] += 1

        return {
            "total_tasks": total,
            "successful_tasks": successful,
            "success_rate": successful / total if total > 0 else 0,
            "by_agent": by_agent
        }

    async def recommend_agent(self, task_description: str) -> str:
        """智能推荐最适合的 Agent"""
        if not self.llm:
            return self._match_agent_type(task_description) or "general"

        available = ", ".join([
            f"{p.agent_type}({p.name}): {p.description}"
            for p in self._registry.values()
        ])

        prompt = f"""根据任务描述，推荐最适合的执行者。

任务：{task_description}

可用执行者：
{available}

只返回执行者类型（如 researcher），不要其他内容。"""

        try:
            response = await self.llm.chat([{"role": "user", "content": prompt}])
            agent_type = response.strip().lower()
            if agent_type in self._registry:
                return agent_type
        except:
            pass

        return self._match_agent_type(task_description) or "general"
