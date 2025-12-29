"""顾问团 (Advisory Layer) - 思维框架与多元视角

设计原则：
- 思维框架，非固定人设
- 按需咨询，只提供建议
- 不参与执行

6 个基础视角：
- strategic: 战略视角
- product: 产品视角
- technical: 技术视角
- user: 用户视角
- business: 商业视角
- risk: 风险视角
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Perspective(str, Enum):
    """思维视角"""
    STRATEGIC = "strategic"    # 战略视角
    PRODUCT = "product"        # 产品视角
    TECHNICAL = "technical"    # 技术视角
    USER = "user"              # 用户视角
    BUSINESS = "business"      # 商业视角
    RISK = "risk"              # 风险视角


@dataclass
class PerspectiveProfile:
    """视角配置"""
    perspective: Perspective
    name: str
    description: str
    focus_areas: list[str]
    key_questions: list[str]
    thinking_prompt: str


# 视角配置
PERSPECTIVE_PROFILES: dict[Perspective, PerspectiveProfile] = {
    Perspective.STRATEGIC: PerspectiveProfile(
        perspective=Perspective.STRATEGIC,
        name="战略视角",
        description="着眼全局与长期，关注方向和定位",
        focus_areas=["长期影响", "竞争格局", "资源配置", "核心优势", "战略定位"],
        key_questions=[
            "这对长期发展有什么影响？",
            "竞争对手会如何应对？",
            "这是否符合核心战略？",
            "资源投入是否值得？"
        ],
        thinking_prompt="""从战略角度分析这个问题：
- 考虑长期影响和可持续性
- 分析竞争格局和市场定位
- 评估资源投入与预期收益
- 识别战略机会和威胁"""
    ),
    Perspective.PRODUCT: PerspectiveProfile(
        perspective=Perspective.PRODUCT,
        name="产品视角",
        description="以用户需求为中心，关注价值交付",
        focus_areas=["用户需求", "功能优先级", "产品体验", "迭代规划", "MVP"],
        key_questions=[
            "用户真正需要什么？",
            "这个功能的优先级如何？",
            "最小可行方案是什么？",
            "如何验证这个假设？"
        ],
        thinking_prompt="""从产品角度分析这个问题：
- 明确目标用户和核心需求
- 评估功能优先级和 ROI
- 考虑产品体验和易用性
- 规划 MVP 和迭代路径"""
    ),
    Perspective.TECHNICAL: PerspectiveProfile(
        perspective=Perspective.TECHNICAL,
        name="技术视角",
        description="关注可行性、架构和实现质量",
        focus_areas=["技术可行性", "系统架构", "性能安全", "技术债务", "可维护性"],
        key_questions=[
            "技术上如何实现？",
            "有哪些技术风险？",
            "对系统架构有什么影响？",
            "如何保证代码质量？"
        ],
        thinking_prompt="""从技术角度分析这个问题：
- 评估技术可行性和复杂度
- 考虑系统架构和扩展性
- 识别技术风险和依赖
- 规划实现方案和技术选型"""
    ),
    Perspective.USER: PerspectiveProfile(
        perspective=Perspective.USER,
        name="用户视角",
        description="站在用户角度，理解行为和心理",
        focus_areas=["用户行为", "心理动机", "使用场景", "痛点需求", "体验感受"],
        key_questions=[
            "用户会如何使用？",
            "用户的心理动机是什么？",
            "使用过程中有什么痛点？",
            "用户会有什么感受？"
        ],
        thinking_prompt="""从用户角度分析这个问题：
- 模拟用户的使用场景和流程
- 理解用户的心理动机和期望
- 识别用户痛点和困惑
- 预测用户行为和反馈"""
    ),
    Perspective.BUSINESS: PerspectiveProfile(
        perspective=Perspective.BUSINESS,
        name="商业视角",
        description="关注商业价值和可持续性",
        focus_areas=["商业模式", "成本收益", "市场机会", "盈利能力", "增长潜力"],
        key_questions=[
            "这能带来什么商业价值？",
            "成本和收益如何？",
            "商业模式是否可持续？",
            "如何实现盈利？"
        ],
        thinking_prompt="""从商业角度分析这个问题：
- 评估商业价值和市场机会
- 分析成本结构和盈利模式
- 考虑商业可持续性
- 识别增长杠杆和变现路径"""
    ),
    Perspective.RISK: PerspectiveProfile(
        perspective=Perspective.RISK,
        name="风险视角",
        description="识别潜在风险和合规要求",
        focus_areas=["潜在风险", "法规合规", "安全隐患", "应急预案", "风险缓解"],
        key_questions=[
            "有哪些潜在风险？",
            "是否符合法规要求？",
            "最坏情况是什么？",
            "如何降低风险？"
        ],
        thinking_prompt="""从风险角度分析这个问题：
- 识别潜在风险和不确定性
- 检查法规合规要求
- 评估最坏情况和影响
- 制定风险缓解措施"""
    )
}


@dataclass
class AdvisorOpinion:
    """顾问意见"""
    perspective: Perspective
    opinion: str
    key_points: list[str]
    concerns: list[str]
    suggestions: list[str]


class AdvisorySystem:
    """顾问系统 - 提供多元视角的建议"""

    def __init__(self, llm_provider=None, knowledge_base=None):
        self.llm = llm_provider
        self.knowledge_base = knowledge_base

    async def get_perspective(
        self,
        perspective: Perspective,
        context: str,
        specific_question: str = None
    ) -> AdvisorOpinion:
        """获取特定视角的建议"""
        profile = PERSPECTIVE_PROFILES[perspective]

        if not self.llm:
            # 无 LLM 时返回框架性建议
            return AdvisorOpinion(
                perspective=perspective,
                opinion=f"从{profile.name}考虑：{profile.description}",
                key_points=profile.focus_areas,
                concerns=[],
                suggestions=profile.key_questions
            )

        # 检索相关知识
        knowledge_context = ""
        if self.knowledge_base:
            results = self.knowledge_base.search(context, top_k=3)
            if results:
                knowledge_context = "\n\n相关知识：\n" + "\n".join([
                    f"- {r.knowledge.title}: {r.knowledge.content[:200]}..."
                    for r in results
                ])

        # 构建 prompt
        question_part = f"\n\n具体问题：{specific_question}" if specific_question else ""

        prompt = f"""{profile.thinking_prompt}

任务/问题：
{context}{question_part}{knowledge_context}

请从{profile.name}提供分析，返回 JSON 格式：
{{
  "opinion": "核心观点（1-2句话）",
  "key_points": ["要点1", "要点2", "要点3"],
  "concerns": ["担忧1", "担忧2"],
  "suggestions": ["建议1", "建议2"]
}}

只返回 JSON，不要其他内容。"""

        try:
            response = await self.llm.chat([{"role": "user", "content": prompt}])
            data = self._parse_json(response)

            return AdvisorOpinion(
                perspective=perspective,
                opinion=data.get("opinion", ""),
                key_points=data.get("key_points", []),
                concerns=data.get("concerns", []),
                suggestions=data.get("suggestions", [])
            )

        except Exception as e:
            print(f"获取 {profile.name} 建议失败: {e}")
            return AdvisorOpinion(
                perspective=perspective,
                opinion=f"分析失败: {str(e)}",
                key_points=[],
                concerns=[],
                suggestions=[]
            )

    def _parse_json(self, text: str) -> dict:
        """解析 JSON，处理可能的格式问题"""
        import json

        # 尝试直接解析
        try:
            return json.loads(text)
        except:
            pass

        # 尝试提取 JSON 块
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass

        return {}

    async def consult(
        self,
        context: str,
        perspectives: list[Perspective] = None,
        specific_question: str = None
    ) -> list[AdvisorOpinion]:
        """咨询顾问团（多个视角）"""
        if perspectives is None:
            # 自动选择视角
            perspectives = await self._auto_select_perspectives(context)

        opinions = []
        for perspective in perspectives:
            opinion = await self.get_perspective(perspective, context, specific_question)
            opinions.append(opinion)

        return opinions

    async def _auto_select_perspectives(self, context: str) -> list[Perspective]:
        """自动选择合适的视角"""
        if not self.llm:
            # 默认返回三个核心视角
            return [Perspective.STRATEGIC, Perspective.PRODUCT, Perspective.TECHNICAL]

        perspective_list = "\n".join([
            f"- {p.value}: {PERSPECTIVE_PROFILES[p].name} - {PERSPECTIVE_PROFILES[p].description}"
            for p in Perspective
        ])

        prompt = f"""根据以下任务，选择 2-3 个最相关的分析视角。

任务：
{context}

可选视角：
{perspective_list}

直接返回视角 ID，用逗号分隔，例如：strategic,product,technical
不要返回其他内容。"""

        try:
            response = await self.llm.chat([{"role": "user", "content": prompt}])

            selected = []
            for part in response.strip().split(","):
                part = part.strip().lower()
                try:
                    selected.append(Perspective(part))
                except ValueError:
                    continue

            return selected if selected else [Perspective.STRATEGIC, Perspective.PRODUCT, Perspective.TECHNICAL]

        except Exception as e:
            print(f"自动选择视角失败: {e}")
            return [Perspective.STRATEGIC, Perspective.PRODUCT, Perspective.TECHNICAL]

    def get_all_perspectives(self) -> list[dict]:
        """获取所有可用视角"""
        return [
            {
                "id": p.value,
                "name": profile.name,
                "description": profile.description,
                "focus_areas": profile.focus_areas,
                "key_questions": profile.key_questions
            }
            for p, profile in PERSPECTIVE_PROFILES.items()
        ]

    async def synthesize_opinions(self, opinions: list[AdvisorOpinion], context: str) -> str:
        """综合多个视角的意见"""
        if not opinions:
            return "暂无顾问意见"

        if not self.llm:
            # 简单拼接
            parts = []
            for op in opinions:
                profile = PERSPECTIVE_PROFILES[op.perspective]
                parts.append(f"【{profile.name}】{op.opinion}")
            return "\n\n".join(parts)

        opinions_text = "\n\n".join([
            f"【{PERSPECTIVE_PROFILES[op.perspective].name}】\n"
            f"观点：{op.opinion}\n"
            f"要点：{', '.join(op.key_points)}\n"
            f"担忧：{', '.join(op.concerns)}\n"
            f"建议：{', '.join(op.suggestions)}"
            for op in opinions
        ])

        prompt = f"""综合以下多个视角的分析，生成一个简洁的综合建议。

任务背景：
{context}

各视角分析：
{opinions_text}

请综合各方观点，给出：
1. 核心结论（1-2句话）
2. 关键行动建议（3-5条）
3. 需要注意的风险

控制在 200 字以内。"""

        try:
            return await self.llm.chat([{"role": "user", "content": prompt}])
        except Exception as e:
            return f"综合意见失败: {e}"
