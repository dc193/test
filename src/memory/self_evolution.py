"""Self Evolution System - 自进化系统

实现 AI 公司的自我进化能力：
1. 任务执行时召唤专家知识
2. 记录知识使用和效果
3. 任务完成后自动提炼经验
4. 发现知识缺口
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from datetime import datetime
import json
from pathlib import Path

from .knowledge_base import KnowledgeBase, Knowledge, KnowledgeType, RetrievalResult
from .expert_system import (
    ExpertPersona, ExpertMatcher, EvolutionTracker,
    EXPERT_PROFILES, KnowledgeEvolution
)

if TYPE_CHECKING:
    from ..core.llm import LLMProvider


@dataclass
class TaskContext:
    """任务上下文"""
    task_id: str
    description: str
    domain: str = ""  # 领域：finance, tech, marketing 等
    required_personas: list[str] = field(default_factory=list)
    summoned_knowledge: list[str] = field(default_factory=list)  # 使用的知识 ID
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    outcome: Optional[str] = None  # success, partial, failed
    user_feedback: Optional[str] = None
    lessons_learned: Optional[str] = None


@dataclass
class KnowledgeGap:
    """知识缺口"""
    id: str
    description: str
    domain: str
    discovered_at: str
    task_id: str
    suggested_sources: list[str] = field(default_factory=list)
    resolved: bool = False
    resolution_knowledge_id: Optional[str] = None


class SelfEvolvingKnowledge:
    """自进化知识系统

    核心能力：
    - 专家召唤：根据任务匹配最相关的专家知识
    - 使用追踪：记录哪些知识被用到
    - 反馈学习：根据任务结果更新知识置信度
    - 经验提炼：从完成的任务中学习新知识
    - 缺口发现：识别需要补充的知识领域

    防护机制：
    - 学习冷却时间：避免频繁学习消耗 token
    - 每日学习配额：限制每天自动学习次数
    - 相似知识检测：避免重复学习相同内容
    """

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        llm_provider: Optional["LLMProvider"] = None,
        data_dir: str = "data/knowledge",
        # 防护配置
        learning_cooldown_seconds: int = 60,  # 学习冷却时间（秒）
        daily_learning_quota: int = 20,       # 每日学习配额
        similarity_threshold: float = 0.85    # 相似度阈值（超过则视为重复）
    ):
        self.kb = knowledge_base
        self.llm = llm_provider
        self.data_dir = Path(data_dir)

        # 专家匹配器
        self.expert_matcher = ExpertMatcher(llm_provider)

        # 进化追踪器
        self.evolution_tracker = EvolutionTracker(data_dir)

        # 防护机制配置
        self.learning_cooldown_seconds = learning_cooldown_seconds
        self.daily_learning_quota = daily_learning_quota
        self.similarity_threshold = similarity_threshold

        # 防护状态
        self._last_learning_time: Optional[datetime] = None
        self._daily_learning_count = 0
        self._last_reset_date: Optional[str] = None
        self._load_protection_state()

        # 知识缺口
        self.gaps_file = self.data_dir / "knowledge_gaps.json"
        self._gaps: dict[str, KnowledgeGap] = {}
        self._load_gaps()

        # 当前任务上下文
        self._current_tasks: dict[str, TaskContext] = {}

    def _load_gaps(self):
        """加载知识缺口"""
        if self.gaps_file.exists():
            try:
                with open(self.gaps_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self._gaps[k] = KnowledgeGap(**v)
            except Exception as e:
                print(f"加载知识缺口失败: {e}")

    def _save_gaps(self):
        """保存知识缺口"""
        with open(self.gaps_file, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.__dict__ for k, v in self._gaps.items()},
                f,
                ensure_ascii=False,
                indent=2
            )

    # ==================== 防护机制 ====================

    def _load_protection_state(self):
        """加载防护状态"""
        state_file = self.data_dir / "protection_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._daily_learning_count = data.get("daily_learning_count", 0)
                    self._last_reset_date = data.get("last_reset_date")
                    last_time = data.get("last_learning_time")
                    if last_time:
                        self._last_learning_time = datetime.fromisoformat(last_time)
            except Exception as e:
                print(f"加载防护状态失败: {e}")

    def _save_protection_state(self):
        """保存防护状态"""
        state_file = self.data_dir / "protection_state.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "daily_learning_count": self._daily_learning_count,
                    "last_reset_date": self._last_reset_date,
                    "last_learning_time": self._last_learning_time.isoformat() if self._last_learning_time else None
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存防护状态失败: {e}")

    def _check_can_learn(self) -> tuple[bool, str]:
        """检查是否可以学习

        Returns:
            (can_learn, reason) - 是否可以学习及原因
        """
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        # 检查是否需要重置每日计数
        if self._last_reset_date != today:
            self._daily_learning_count = 0
            self._last_reset_date = today
            self._save_protection_state()

        # 检查每日配额
        if self._daily_learning_count >= self.daily_learning_quota:
            return False, f"已达到每日学习配额 ({self.daily_learning_quota} 次)"

        # 检查冷却时间
        if self._last_learning_time:
            elapsed = (now - self._last_learning_time).total_seconds()
            if elapsed < self.learning_cooldown_seconds:
                remaining = int(self.learning_cooldown_seconds - elapsed)
                return False, f"学习冷却中，还需等待 {remaining} 秒"

        return True, "可以学习"

    def _record_learning(self):
        """记录一次学习"""
        self._last_learning_time = datetime.now()
        self._daily_learning_count += 1
        self._save_protection_state()

    def _check_similar_knowledge_exists(self, content: str) -> tuple[bool, Optional[str]]:
        """检查是否已存在相似知识

        Args:
            content: 要检查的内容

        Returns:
            (exists, existing_id) - 是否存在相似知识及其ID
        """
        # 搜索相似内容
        results = self.kb.search(content, top_k=3)

        for result in results:
            if result.score >= self.similarity_threshold:
                return True, result.knowledge.id

        return False, None

    def get_protection_status(self) -> dict:
        """获取防护状态"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        # 检查是否需要重置
        if self._last_reset_date != today:
            remaining_quota = self.daily_learning_quota
        else:
            remaining_quota = max(0, self.daily_learning_quota - self._daily_learning_count)

        # 计算冷却剩余时间
        cooldown_remaining = 0
        if self._last_learning_time:
            elapsed = (now - self._last_learning_time).total_seconds()
            if elapsed < self.learning_cooldown_seconds:
                cooldown_remaining = int(self.learning_cooldown_seconds - elapsed)

        return {
            "daily_quota": self.daily_learning_quota,
            "remaining_quota": remaining_quota,
            "used_today": self._daily_learning_count,
            "cooldown_seconds": self.learning_cooldown_seconds,
            "cooldown_remaining": cooldown_remaining,
            "similarity_threshold": self.similarity_threshold,
            "can_learn": cooldown_remaining == 0 and remaining_quota > 0
        }

    # ==================== 专家召唤 ====================

    async def summon_experts(
        self,
        task_description: str,
        domain: str = "",
        top_k: int = 5
    ) -> list[RetrievalResult]:
        """召唤专家知识

        根据任务描述，找到最相关的专家知识

        Args:
            task_description: 任务描述
            domain: 领域提示（可选）
            top_k: 返回数量

        Returns:
            相关知识列表
        """
        # 1. 识别需要哪些专家
        personas = await self.expert_matcher.match_experts_by_ai(
            task_description,
            context=f"领域: {domain}" if domain else ""
        )

        # 2. 基于专家角色搜索知识
        if personas:
            results = self.kb.search_with_personas(
                query=task_description,
                personas=[p.value for p in personas],
                top_k=top_k
            )
        else:
            # 降级为普通搜索
            results = self.kb.search(task_description, top_k=top_k)

        return results

    def get_expert_advice(
        self,
        task_description: str,
        persona: ExpertPersona
    ) -> list[RetrievalResult]:
        """获取特定专家的建议

        Args:
            task_description: 任务描述
            persona: 专家角色

        Returns:
            该专家视角的相关知识
        """
        return self.kb.search_with_personas(
            query=task_description,
            personas=[persona.value],
            top_k=3
        )

    # ==================== 任务追踪 ====================

    def start_task(
        self,
        task_id: str,
        description: str,
        domain: str = "",
        required_personas: list[str] = None
    ) -> TaskContext:
        """开始一个任务"""
        context = TaskContext(
            task_id=task_id,
            description=description,
            domain=domain,
            required_personas=required_personas or []
        )
        self._current_tasks[task_id] = context
        return context

    def record_knowledge_usage(self, task_id: str, knowledge_id: str):
        """记录知识使用"""
        if task_id in self._current_tasks:
            context = self._current_tasks[task_id]
            if knowledge_id not in context.summoned_knowledge:
                context.summoned_knowledge.append(knowledge_id)

            # 同时更新进化追踪
            self.evolution_tracker.record_usage(
                knowledge_id=knowledge_id,
                task_id=task_id,
                task_description=context.description
            )

    def complete_task(
        self,
        task_id: str,
        outcome: str = "success",
        user_feedback: str = ""
    ) -> Optional[TaskContext]:
        """完成任务

        Args:
            task_id: 任务 ID
            outcome: 结果（success / partial / failed）
            user_feedback: 用户反馈
        """
        if task_id not in self._current_tasks:
            return None

        context = self._current_tasks[task_id]
        context.completed_at = datetime.now().isoformat()
        context.outcome = outcome
        context.user_feedback = user_feedback

        # 更新使用的知识的成功率
        was_helpful = outcome == "success"
        for knowledge_id in context.summoned_knowledge:
            self.evolution_tracker.record_feedback(knowledge_id, was_helpful)

        return context

    # ==================== 经验学习 ====================

    async def learn_from_task(
        self,
        task_id: str,
        task_result: str,
        force: bool = False
    ) -> tuple[Optional[Knowledge], str]:
        """从完成的任务中学习

        分析任务执行过程，提炼可复用的经验

        Args:
            task_id: 任务 ID
            task_result: 任务执行结果
            force: 是否强制学习（跳过防护检查）

        Returns:
            (knowledge, message) - 新学到的知识和消息
        """
        if not self.llm:
            return None, "未配置 LLM Provider"

        context = self._current_tasks.get(task_id)
        if not context:
            return None, f"未找到任务: {task_id}"

        # 防护检查（除非强制）
        if not force:
            can_learn, reason = self._check_can_learn()
            if not can_learn:
                return None, f"学习被阻止: {reason}"

        # 构建分析 prompt
        prompt = f"""分析以下任务执行过程，提炼可复用的经验教训。

## 任务
{context.description}

## 领域
{context.domain or '通用'}

## 执行结果
{task_result}

## 结果评估
{context.outcome or '未知'}

{f"## 用户反馈\n{context.user_feedback}" if context.user_feedback else ""}

---

请分析：

1. **关键成功/失败因素**：是什么导致了这个结果？

2. **可复用的经验**：从这次任务中可以提炼出什么通用经验？
   - 什么场景下适用？
   - 具体怎么做？
   - 要避免什么？

3. **值得记录吗？**
   如果这个经验有价值（对未来类似任务有帮助），请以下面格式输出：

```json
{{
    "should_save": true,
    "title": "经验的标题",
    "knowledge_type": "methodology / behavior_principle / insight",
    "personas": ["适用的专家角色"],
    "perspective": "这个经验的视角",
    "content": "详细的经验内容"
}}
```

如果没有值得记录的新经验，输出：
```json
{{"should_save": false, "reason": "原因"}}
```
"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.chat(messages)

            # 解析 JSON
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if not json_match:
                return None, "无法解析 LLM 响应"

            data = json.loads(json_match.group(1))

            if not data.get("should_save"):
                reason = data.get('reason', '无新经验')
                print(f"任务 {task_id} 没有产生新的可记录经验: {reason}")
                return None, f"无需保存: {reason}"

            # 检查相似知识（除非强制）
            content = data.get("content", "")
            if not force:
                exists, existing_id = self._check_similar_knowledge_exists(content)
                if exists:
                    return None, f"已存在相似知识 (ID: {existing_id})，跳过保存"

            # 存入知识库
            knowledge_type = KnowledgeType.METHODOLOGY
            type_str = data.get("knowledge_type", "methodology")
            try:
                knowledge_type = KnowledgeType(type_str)
            except ValueError:
                pass

            knowledge = self.kb.add(
                content=content,
                knowledge_type=knowledge_type,
                title=f"[任务学习] {data.get('title', task_id)}",
                source=f"task:{task_id}",
                tags=["自动学习", context.domain] if context.domain else ["自动学习"],
                metadata={
                    "source_type": "task_learning",
                    "task_id": task_id,
                    "outcome": context.outcome
                },
                personas=data.get("personas", []),
                perspective=data.get("perspective", "")
            )

            # 记录学习（更新防护状态）
            self._record_learning()

            context.lessons_learned = knowledge.id
            print(f"从任务 {task_id} 学到新知识: {knowledge.title}")

            return knowledge, f"成功学习: {knowledge.title}"

        except Exception as e:
            print(f"从任务学习失败: {e}")
            return None, f"学习失败: {str(e)}"

    # ==================== 缺口发现 ====================

    async def discover_knowledge_gap(
        self,
        task_description: str,
        task_id: str,
        failure_reason: str = "",
        force: bool = False
    ) -> tuple[Optional[KnowledgeGap], str]:
        """发现知识缺口

        当任务执行遇到困难时，分析是否存在知识缺口

        Args:
            task_description: 任务描述
            task_id: 任务 ID
            failure_reason: 失败原因
            force: 是否强制分析（跳过防护检查）

        Returns:
            (gap, message) - 知识缺口和消息
        """
        if not self.llm:
            return None, "未配置 LLM Provider"

        # 防护检查（除非强制）
        if not force:
            can_learn, reason = self._check_can_learn()
            if not can_learn:
                return None, f"分析被阻止: {reason}"

        prompt = f"""分析以下任务执行困难的原因，判断是否存在知识缺口。

## 任务
{task_description}

## 遇到的问题
{failure_reason or '任务执行困难，原因不明'}

---

请分析：

1. 这个问题是否因为缺少某方面的知识？
2. 如果是，缺少的是什么类型的知识？
3. 建议从哪些来源补充？

以 JSON 格式输出：
```json
{{
    "has_gap": true/false,
    "gap_description": "缺少的知识描述",
    "domain": "知识所属领域",
    "suggested_sources": ["建议的学习来源1", "建议的学习来源2"]
}}
```
"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.chat(messages)

            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if not json_match:
                return None, "无法解析 LLM 响应"

            data = json.loads(json_match.group(1))

            if not data.get("has_gap"):
                return None, "未发现知识缺口"

            # 检查是否已存在相同描述的缺口
            gap_desc = data.get("gap_description", "")
            for existing_gap in self._gaps.values():
                if existing_gap.description == gap_desc and not existing_gap.resolved:
                    return None, f"已存在相同的知识缺口 (ID: {existing_gap.id})"

            # 创建知识缺口记录
            import hashlib
            gap_id = f"gap_{hashlib.md5(gap_desc.encode()).hexdigest()[:8]}"

            gap = KnowledgeGap(
                id=gap_id,
                description=gap_desc,
                domain=data.get("domain", ""),
                discovered_at=datetime.now().isoformat(),
                task_id=task_id,
                suggested_sources=data.get("suggested_sources", [])
            )

            self._gaps[gap_id] = gap
            self._save_gaps()

            # 记录学习（更新防护状态）
            self._record_learning()

            print(f"发现知识缺口: {gap.description}")
            return gap, f"发现知识缺口: {gap.description}"

        except Exception as e:
            print(f"发现知识缺口失败: {e}")
            return None, f"分析失败: {str(e)}"

    def get_unresolved_gaps(self) -> list[KnowledgeGap]:
        """获取未解决的知识缺口"""
        return [g for g in self._gaps.values() if not g.resolved]

    def resolve_gap(self, gap_id: str, knowledge_id: str):
        """标记知识缺口已解决"""
        if gap_id in self._gaps:
            self._gaps[gap_id].resolved = True
            self._gaps[gap_id].resolution_knowledge_id = knowledge_id
            self._save_gaps()

    # ==================== 统计与洞察 ====================

    def get_evolution_stats(self) -> dict:
        """获取进化统计"""
        evolution_stats = self.evolution_tracker.get_stats()
        gaps_stats = {
            "total_gaps": len(self._gaps),
            "unresolved_gaps": len(self.get_unresolved_gaps())
        }
        return {
            **evolution_stats,
            **gaps_stats,
            "active_tasks": len(self._current_tasks)
        }

    def get_top_knowledge(self, limit: int = 10) -> list[tuple[Knowledge, KnowledgeEvolution]]:
        """获取表现最好的知识"""
        top_evolutions = self.evolution_tracker.get_top_performing(limit)
        results = []
        for knowledge_id, evolution in top_evolutions:
            knowledge = self.kb._knowledge_meta.get(knowledge_id)
            if knowledge:
                results.append((knowledge, evolution))
        return results

    def get_underperforming_knowledge(self) -> list[tuple[Knowledge, KnowledgeEvolution]]:
        """获取表现不佳的知识"""
        underperforming = self.evolution_tracker.get_underperforming()
        results = []
        for knowledge_id, evolution in underperforming:
            knowledge = self.kb._knowledge_meta.get(knowledge_id)
            if knowledge:
                results.append((knowledge, evolution))
        return results
