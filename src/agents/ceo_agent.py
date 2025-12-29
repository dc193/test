"""CEO 层 (CEO Agent) - 决策与执行

职责：
- 接收用户任务
- 理解意图，分析需求
- 咨询顾问团获取多元视角
- 检索知识库获取相关知识
- 综合决策，生成输出
- 记录任务结果供上帝层分析
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Any

from .advisory import AdvisorySystem, Perspective, AdvisorOpinion
from .god_layer import GodLayer, TaskRecord


@dataclass
class Task:
    """任务"""
    id: str
    description: str
    context: str = ""
    constraints: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def create(cls, description: str, context: str = "", constraints: list[str] = None) -> "Task":
        return cls(
            id=f"task_{uuid.uuid4().hex[:8]}",
            description=description,
            context=context,
            constraints=constraints or []
        )


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: str  # "success", "failed", "partial"
    output: str
    perspectives_consulted: list[str] = field(default_factory=list)
    knowledge_used: list[str] = field(default_factory=list)
    reasoning: str = ""
    completed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class CEOAgent:
    """CEO 智能体 - 核心决策与执行层"""

    def __init__(
        self,
        llm_provider=None,
        knowledge_base=None,
        advisory_system: AdvisorySystem = None,
        god_layer: GodLayer = None,
        tools: dict[str, Callable] = None
    ):
        self.llm = llm_provider
        self.knowledge_base = knowledge_base
        self.advisory = advisory_system or AdvisorySystem(llm_provider, knowledge_base)
        self.god_layer = god_layer
        self.tools = tools or {}

        # 工作记忆（当前会话）
        self._working_memory: list[dict] = []
        self._current_task: Optional[Task] = None

    async def handle_task(
        self,
        task: Task,
        perspectives: list[Perspective] = None,
        skip_advisory: bool = False
    ) -> TaskResult:
        """处理任务 - CEO 的核心工作流程"""
        self._current_task = task

        try:
            # 1. 理解任务
            task_analysis = await self._analyze_task(task)

            # 2. 检索相关知识
            knowledge_results = await self._search_knowledge(task)
            knowledge_used = [r.knowledge.id for r in knowledge_results]

            # 3. 咨询顾问团（可选）
            advisor_opinions = []
            perspectives_consulted = []
            if not skip_advisory:
                advisor_opinions = await self.advisory.consult(
                    context=f"{task.description}\n{task.context}",
                    perspectives=perspectives
                )
                perspectives_consulted = [op.perspective.value for op in advisor_opinions]

            # 4. 综合决策
            decision = await self._make_decision(
                task=task,
                analysis=task_analysis,
                knowledge=knowledge_results,
                opinions=advisor_opinions
            )

            # 5. 执行任务
            output = await self._execute(task, decision)

            # 6. 构建结果
            result = TaskResult(
                task_id=task.id,
                status="success",
                output=output,
                perspectives_consulted=perspectives_consulted,
                knowledge_used=knowledge_used,
                reasoning=decision
            )

        except Exception as e:
            result = TaskResult(
                task_id=task.id,
                status="failed",
                output=f"任务失败: {str(e)}",
                reasoning=str(e)
            )

        # 7. 记录到上帝层
        if self.god_layer:
            self._report_to_god_layer(task, result)

        self._current_task = None
        return result

    async def _analyze_task(self, task: Task) -> str:
        """分析任务意图"""
        if not self.llm:
            return f"任务类型: 通用\n目标: {task.description}"

        prompt = f"""分析以下任务：

任务描述：{task.description}
{f"上下文：{task.context}" if task.context else ""}
{f"约束条件：{', '.join(task.constraints)}" if task.constraints else ""}

请简要分析：
1. 任务类型（如：分析、创建、决策、问答）
2. 核心目标
3. 关键要素

控制在 100 字以内。"""

        try:
            return await self.llm.chat([{"role": "user", "content": prompt}])
        except Exception as e:
            return f"任务分析失败: {e}"

    async def _search_knowledge(self, task: Task) -> list:
        """检索相关知识"""
        if not self.knowledge_base:
            return []

        query = f"{task.description} {task.context}"
        return self.knowledge_base.search(query, top_k=5, min_score=0.3)

    async def _make_decision(
        self,
        task: Task,
        analysis: str,
        knowledge: list,
        opinions: list[AdvisorOpinion]
    ) -> str:
        """综合决策"""
        if not self.llm:
            parts = [f"任务分析：{analysis}"]
            if knowledge:
                parts.append(f"相关知识：{len(knowledge)} 条")
            if opinions:
                parts.append(f"顾问意见：{len(opinions)} 个视角")
            return "\n".join(parts)

        # 构建知识上下文
        knowledge_text = ""
        if knowledge:
            knowledge_text = "\n\n相关知识：\n" + "\n".join([
                f"- [{r.knowledge.title}]: {r.knowledge.content[:200]}..."
                for r in knowledge[:3]
            ])

        # 构建顾问意见
        opinions_text = ""
        if opinions:
            from .advisory import PERSPECTIVE_PROFILES
            opinions_text = "\n\n顾问意见：\n" + "\n".join([
                f"- 【{PERSPECTIVE_PROFILES[op.perspective].name}】{op.opinion}"
                for op in opinions
            ])

        prompt = f"""作为 CEO，综合以下信息做出决策。

任务：{task.description}
{f"上下文：{task.context}" if task.context else ""}

任务分析：
{analysis}
{knowledge_text}
{opinions_text}

请给出：
1. 决策方向（1句话）
2. 执行要点（3-5条）
3. 风险提示（如有）

简洁明了，控制在 200 字以内。"""

        try:
            return await self.llm.chat([{"role": "user", "content": prompt}])
        except Exception as e:
            return f"决策失败: {e}"

    async def _execute(self, task: Task, decision: str) -> str:
        """执行任务"""
        if not self.llm:
            return f"决策结果：\n{decision}"

        prompt = f"""根据以下决策，完成任务输出。

任务：{task.description}
{f"上下文：{task.context}" if task.context else ""}

决策：
{decision}

请直接输出任务结果，不要输出决策过程。"""

        try:
            return await self.llm.chat([{"role": "user", "content": prompt}])
        except Exception as e:
            return f"执行失败: {e}"

    def _report_to_god_layer(self, task: Task, result: TaskResult):
        """向上帝层报告任务"""
        record = TaskRecord(
            task_id=task.id,
            description=task.description,
            status=result.status,
            started_at=task.created_at,
            completed_at=result.completed_at,
            perspectives_consulted=result.perspectives_consulted,
            knowledge_used=result.knowledge_used,
            notes=result.reasoning if result.status != "success" else ""
        )
        should_evolve = self.god_layer.record_task(record)

        if should_evolve:
            # 可以在这里触发异步进化，或者返回标志让调用方处理
            print("[CEO] 任务计数达到阈值，建议触发进化")

    # ==================== 便捷方法 ====================

    async def quick_task(self, description: str) -> str:
        """快速执行任务（简化接口）"""
        task = Task.create(description)
        result = await self.handle_task(task)
        return result.output

    async def ask(self, question: str, perspectives: list[Perspective] = None) -> str:
        """问答模式"""
        task = Task.create(
            description=question,
            context="用户提问，需要简洁准确的回答"
        )
        result = await self.handle_task(task, perspectives=perspectives)
        return result.output

    async def analyze(self, topic: str, context: str = "") -> dict:
        """分析模式 - 返回结构化结果"""
        task = Task.create(
            description=f"分析：{topic}",
            context=context
        )

        # 默认咨询所有视角
        all_perspectives = list(Perspective)
        result = await self.handle_task(task, perspectives=all_perspectives)

        return {
            "topic": topic,
            "analysis": result.output,
            "perspectives": result.perspectives_consulted,
            "knowledge_used": result.knowledge_used,
            "status": result.status
        }

    async def decide(self, question: str, options: list[str] = None) -> str:
        """决策模式"""
        context = ""
        if options:
            context = f"可选方案：\n" + "\n".join([f"- {opt}" for opt in options])

        task = Task.create(
            description=f"决策：{question}",
            context=context
        )

        # 决策问题咨询战略和风险视角
        result = await self.handle_task(
            task,
            perspectives=[Perspective.STRATEGIC, Perspective.BUSINESS, Perspective.RISK]
        )
        return result.output

    # ==================== 工作记忆管理 ====================

    def add_to_memory(self, content: str, role: str = "context"):
        """添加到工作记忆"""
        self._working_memory.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def get_memory_context(self, limit: int = 10) -> str:
        """获取工作记忆上下文"""
        recent = self._working_memory[-limit:]
        return "\n".join([
            f"[{m['role']}] {m['content']}"
            for m in recent
        ])

    def clear_memory(self):
        """清空工作记忆"""
        self._working_memory = []

    # ==================== 状态查询 ====================

    def get_status(self) -> dict:
        """获取 CEO 状态"""
        return {
            "current_task": self._current_task.id if self._current_task else None,
            "working_memory_size": len(self._working_memory),
            "has_llm": self.llm is not None,
            "has_knowledge_base": self.knowledge_base is not None,
            "has_god_layer": self.god_layer is not None,
            "available_tools": list(self.tools.keys())
        }
