"""Expert System - 知识人格化与专家系统

将知识库转化为可召唤的专家团队：
- 哲学家、心理学家、增长黑客、工程师...
- 根据任务自动匹配专家
- 追踪知识使用和成功率
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
from pathlib import Path


class ExpertPersona(str, Enum):
    """专家角色 - 知识的人格化标签"""

    # 思维与策略
    PHILOSOPHER = "philosopher"              # 哲学家 - 本质思考、第一性原理
    STRATEGIST = "strategist"                # 战略家 - 长期规划、全局视角
    SYSTEMS_THINKER = "systems_thinker"      # 系统思考者 - 复杂系统、反馈循环

    # 人与行为
    PSYCHOLOGIST = "psychologist"            # 心理学家 - 人类行为、动机
    BEHAVIORAL_ECONOMIST = "behavioral_economist"  # 行为经济学家 - 决策偏见
    UX_DESIGNER = "ux_designer"              # UX设计师 - 用户体验、交互

    # 商业与增长
    GROWTH_HACKER = "growth_hacker"          # 增长黑客 - 用户增长、病毒传播
    PRODUCT_MANAGER = "product_manager"      # 产品经理 - 需求分析、优先级
    ENTREPRENEUR = "entrepreneur"            # 创业者 - 商业模式、风险
    MARKETER = "marketer"                    # 营销专家 - 品牌、传播

    # 技术与工程
    SOFTWARE_ARCHITECT = "software_architect"  # 软件架构师 - 系统设计
    ENGINEER = "engineer"                    # 工程师 - 实现、优化
    DATA_SCIENTIST = "data_scientist"        # 数据科学家 - 数据分析、ML
    DEVOPS = "devops"                        # DevOps - 部署、运维

    # 领域专家
    FINANCE_EXPERT = "finance_expert"        # 金融专家
    LEGAL_EXPERT = "legal_expert"            # 法律专家
    DOMAIN_EXPERT = "domain_expert"          # 领域专家（通用）

    # 创意与设计
    DESIGNER = "designer"                    # 设计师 - 视觉、美学
    STORYTELLER = "storyteller"              # 故事讲述者 - 叙事、情感
    CREATIVE_DIRECTOR = "creative_director"  # 创意总监


@dataclass
class ExpertProfile:
    """专家档案"""
    persona: ExpertPersona
    display_name: str
    description: str
    keywords: list[str]  # 用于自动匹配的关键词
    thinking_style: str  # 这个专家如何思考问题


# 专家档案库
EXPERT_PROFILES: dict[ExpertPersona, ExpertProfile] = {
    ExpertPersona.PHILOSOPHER: ExpertProfile(
        persona=ExpertPersona.PHILOSOPHER,
        display_name="哲学家",
        description="追问本质，探索第一性原理",
        keywords=["本质", "为什么", "原理", "意义", "价值", "存在", "真理", "逻辑"],
        thinking_style="从根本假设出发，质疑一切，追求本质理解"
    ),
    ExpertPersona.STRATEGIST: ExpertProfile(
        persona=ExpertPersona.STRATEGIST,
        display_name="战略家",
        description="着眼全局，规划长远",
        keywords=["战略", "长期", "全局", "竞争", "定位", "资源", "目标"],
        thinking_style="分析竞争格局，识别关键杠杆点，制定长期计划"
    ),
    ExpertPersona.SYSTEMS_THINKER: ExpertProfile(
        persona=ExpertPersona.SYSTEMS_THINKER,
        display_name="系统思考者",
        description="理解复杂系统的反馈与涌现",
        keywords=["系统", "反馈", "循环", "涌现", "复杂", "动态", "平衡"],
        thinking_style="识别系统中的反馈循环，理解非线性关系"
    ),
    ExpertPersona.PSYCHOLOGIST: ExpertProfile(
        persona=ExpertPersona.PSYCHOLOGIST,
        display_name="心理学家",
        description="理解人类行为与动机",
        keywords=["心理", "动机", "情绪", "行为", "认知", "习惯", "人性"],
        thinking_style="分析行为背后的心理动机，理解人的认知模式"
    ),
    ExpertPersona.BEHAVIORAL_ECONOMIST: ExpertProfile(
        persona=ExpertPersona.BEHAVIORAL_ECONOMIST,
        display_name="行为经济学家",
        description="研究决策偏见与非理性",
        keywords=["偏见", "决策", "非理性", "激励", "博弈", "损失厌恶"],
        thinking_style="识别决策中的认知偏见，设计有效激励机制"
    ),
    ExpertPersona.UX_DESIGNER: ExpertProfile(
        persona=ExpertPersona.UX_DESIGNER,
        display_name="UX设计师",
        description="优化用户体验与交互",
        keywords=["体验", "交互", "界面", "易用", "用户", "设计", "流程"],
        thinking_style="从用户视角出发，简化流程，减少摩擦"
    ),
    ExpertPersona.GROWTH_HACKER: ExpertProfile(
        persona=ExpertPersona.GROWTH_HACKER,
        display_name="增长黑客",
        description="驱动用户增长与留存",
        keywords=["增长", "留存", "转化", "病毒", "获客", "漏斗", "AARRR"],
        thinking_style="找到增长杠杆，设计病毒循环，优化转化漏斗"
    ),
    ExpertPersona.PRODUCT_MANAGER: ExpertProfile(
        persona=ExpertPersona.PRODUCT_MANAGER,
        display_name="产品经理",
        description="定义产品方向与优先级",
        keywords=["产品", "需求", "优先级", "迭代", "MVP", "功能", "路线图"],
        thinking_style="平衡用户需求与商业目标，确定最小可行方案"
    ),
    ExpertPersona.ENTREPRENEUR: ExpertProfile(
        persona=ExpertPersona.ENTREPRENEUR,
        display_name="创业者",
        description="商业模式与风险把控",
        keywords=["创业", "商业模式", "风险", "机会", "融资", "市场"],
        thinking_style="识别市场机会，验证商业假设，快速迭代"
    ),
    ExpertPersona.MARKETER: ExpertProfile(
        persona=ExpertPersona.MARKETER,
        display_name="营销专家",
        description="品牌建设与市场传播",
        keywords=["营销", "品牌", "传播", "定位", "故事", "渠道"],
        thinking_style="理解目标用户，构建品牌叙事，选择传播渠道"
    ),
    ExpertPersona.SOFTWARE_ARCHITECT: ExpertProfile(
        persona=ExpertPersona.SOFTWARE_ARCHITECT,
        display_name="软件架构师",
        description="系统设计与技术决策",
        keywords=["架构", "设计", "模块", "扩展", "性能", "可维护"],
        thinking_style="权衡技术方案，设计可扩展架构，控制复杂度"
    ),
    ExpertPersona.ENGINEER: ExpertProfile(
        persona=ExpertPersona.ENGINEER,
        display_name="工程师",
        description="高质量代码实现",
        keywords=["代码", "实现", "调试", "优化", "测试", "重构"],
        thinking_style="写出清晰、可维护、高效的代码"
    ),
    ExpertPersona.DATA_SCIENTIST: ExpertProfile(
        persona=ExpertPersona.DATA_SCIENTIST,
        display_name="数据科学家",
        description="数据分析与机器学习",
        keywords=["数据", "分析", "机器学习", "模型", "预测", "特征"],
        thinking_style="用数据验证假设，构建预测模型"
    ),
    ExpertPersona.FINANCE_EXPERT: ExpertProfile(
        persona=ExpertPersona.FINANCE_EXPERT,
        display_name="金融专家",
        description="财务分析与投资决策",
        keywords=["金融", "投资", "财务", "估值", "风险", "收益", "ROI"],
        thinking_style="分析财务数据，评估风险收益，做出投资决策"
    ),
    ExpertPersona.DESIGNER: ExpertProfile(
        persona=ExpertPersona.DESIGNER,
        display_name="设计师",
        description="视觉与美学",
        keywords=["设计", "视觉", "美学", "配色", "排版", "品味"],
        thinking_style="追求视觉美感与功能的平衡"
    ),
    ExpertPersona.STORYTELLER: ExpertProfile(
        persona=ExpertPersona.STORYTELLER,
        display_name="故事讲述者",
        description="叙事与情感连接",
        keywords=["故事", "叙事", "情感", "共鸣", "表达", "沟通"],
        thinking_style="用故事建立情感连接，传递核心信息"
    ),
}


@dataclass
class KnowledgeUsageRecord:
    """知识使用记录"""
    knowledge_id: str
    task_id: str
    task_description: str
    used_at: str
    was_helpful: Optional[bool] = None  # 用户反馈
    outcome: Optional[str] = None  # 结果描述


@dataclass
class KnowledgeEvolution:
    """知识进化追踪"""
    knowledge_id: str
    confidence: float = 0.5  # 置信度 0-1
    applied_count: int = 0   # 使用次数
    success_count: int = 0   # 成功次数
    last_applied: Optional[str] = None
    usage_history: list[KnowledgeUsageRecord] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.applied_count == 0:
            return 0.0
        return self.success_count / self.applied_count

    def record_usage(self, task_id: str, task_description: str, was_helpful: bool = None):
        """记录一次使用"""
        from datetime import datetime
        record = KnowledgeUsageRecord(
            knowledge_id=self.knowledge_id,
            task_id=task_id,
            task_description=task_description,
            used_at=datetime.now().isoformat(),
            was_helpful=was_helpful
        )
        self.usage_history.append(record)
        self.applied_count += 1
        self.last_applied = record.used_at

        if was_helpful is True:
            self.success_count += 1
            # 成功使用增加置信度
            self.confidence = min(1.0, self.confidence + 0.05)
        elif was_helpful is False:
            # 失败使用降低置信度
            self.confidence = max(0.1, self.confidence - 0.1)

    def to_dict(self) -> dict:
        return {
            "knowledge_id": self.knowledge_id,
            "confidence": self.confidence,
            "applied_count": self.applied_count,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "last_applied": self.last_applied,
            "usage_history": [
                {
                    "task_id": r.task_id,
                    "task_description": r.task_description,
                    "used_at": r.used_at,
                    "was_helpful": r.was_helpful,
                    "outcome": r.outcome
                }
                for r in self.usage_history[-10:]  # 只保留最近10条
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeEvolution":
        history = [
            KnowledgeUsageRecord(**r)
            for r in data.get("usage_history", [])
        ]
        return cls(
            knowledge_id=data["knowledge_id"],
            confidence=data.get("confidence", 0.5),
            applied_count=data.get("applied_count", 0),
            success_count=data.get("success_count", 0),
            last_applied=data.get("last_applied"),
            usage_history=history
        )


class ExpertMatcher:
    """专家匹配器 - 根据任务/内容匹配合适的专家"""

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    def match_experts_by_keywords(self, text: str, top_k: int = 3) -> list[ExpertPersona]:
        """基于关键词匹配专家"""
        text_lower = text.lower()
        scores = {}

        for persona, profile in EXPERT_PROFILES.items():
            score = 0
            for keyword in profile.keywords:
                if keyword in text_lower:
                    score += 1
            if score > 0:
                scores[persona] = score

        # 按分数排序
        sorted_experts = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [e[0] for e in sorted_experts[:top_k]]

    async def match_experts_by_ai(self, content: str, context: str = "") -> list[ExpertPersona]:
        """用 AI 匹配最合适的专家角色"""
        if not self.llm:
            return self.match_experts_by_keywords(content)

        # 构建专家列表
        expert_list = "\n".join([
            f"- {p.value}: {EXPERT_PROFILES[p].display_name} - {EXPERT_PROFILES[p].description}"
            for p in ExpertPersona
        ])

        prompt = f"""分析以下内容，判断它最适合哪些专家角色的视角。

内容：
{content}

{f"上下文：{context}" if context else ""}

可选的专家角色：
{expert_list}

请选择 1-3 个最匹配的专家角色，直接返回角色ID（用逗号分隔），不要解释。
例如：philosopher,strategist,engineer"""

        try:
            response = await self.llm.chat([{"role": "user", "content": prompt}])

            # 解析返回的角色
            personas = []
            for part in response.replace(" ", "").split(","):
                part = part.strip().lower()
                try:
                    personas.append(ExpertPersona(part))
                except ValueError:
                    continue

            return personas if personas else self.match_experts_by_keywords(content)

        except Exception as e:
            print(f"AI 匹配专家失败: {e}")
            return self.match_experts_by_keywords(content)


class EvolutionTracker:
    """进化追踪器 - 管理知识的使用和进化"""

    def __init__(self, data_dir: str = "data/knowledge"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.evolution_file = self.data_dir / "knowledge_evolution.json"
        self._evolutions: dict[str, KnowledgeEvolution] = {}
        self._load()

    def _load(self):
        """加载进化数据"""
        if self.evolution_file.exists():
            try:
                with open(self.evolution_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._evolutions = {
                        k: KnowledgeEvolution.from_dict(v)
                        for k, v in data.items()
                    }
            except Exception as e:
                print(f"加载进化数据失败: {e}")

    def _save(self):
        """保存进化数据"""
        with open(self.evolution_file, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.to_dict() for k, v in self._evolutions.items()},
                f,
                ensure_ascii=False,
                indent=2
            )

    def get_evolution(self, knowledge_id: str) -> KnowledgeEvolution:
        """获取或创建知识的进化记录"""
        if knowledge_id not in self._evolutions:
            self._evolutions[knowledge_id] = KnowledgeEvolution(knowledge_id=knowledge_id)
        return self._evolutions[knowledge_id]

    def record_usage(
        self,
        knowledge_id: str,
        task_id: str,
        task_description: str,
        was_helpful: bool = None
    ):
        """记录知识使用"""
        evolution = self.get_evolution(knowledge_id)
        evolution.record_usage(task_id, task_description, was_helpful)
        self._save()

    def record_feedback(self, knowledge_id: str, was_helpful: bool):
        """记录用户反馈（用于最近一次使用）"""
        if knowledge_id in self._evolutions:
            evolution = self._evolutions[knowledge_id]
            if evolution.usage_history:
                last_record = evolution.usage_history[-1]
                last_record.was_helpful = was_helpful
                if was_helpful:
                    evolution.success_count += 1
                    evolution.confidence = min(1.0, evolution.confidence + 0.05)
                else:
                    evolution.confidence = max(0.1, evolution.confidence - 0.1)
                self._save()

    def get_top_performing(self, limit: int = 10) -> list[tuple[str, KnowledgeEvolution]]:
        """获取表现最好的知识"""
        # 按成功率和使用次数综合排序
        sorted_evolutions = sorted(
            self._evolutions.items(),
            key=lambda x: (x[1].success_rate * 0.6 + min(x[1].applied_count / 10, 0.4)),
            reverse=True
        )
        return sorted_evolutions[:limit]

    def get_underperforming(self, min_usage: int = 3) -> list[tuple[str, KnowledgeEvolution]]:
        """获取表现不佳的知识（可能需要淘汰或更新）"""
        return [
            (k, v) for k, v in self._evolutions.items()
            if v.applied_count >= min_usage and v.success_rate < 0.3
        ]

    def get_stats(self) -> dict:
        """获取统计信息"""
        if not self._evolutions:
            return {"total_tracked": 0}

        total_usage = sum(e.applied_count for e in self._evolutions.values())
        total_success = sum(e.success_count for e in self._evolutions.values())

        return {
            "total_tracked": len(self._evolutions),
            "total_usage": total_usage,
            "total_success": total_success,
            "overall_success_rate": total_success / total_usage if total_usage > 0 else 0,
            "high_confidence": len([e for e in self._evolutions.values() if e.confidence > 0.7]),
            "low_confidence": len([e for e in self._evolutions.values() if e.confidence < 0.3])
        }
