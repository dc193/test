"""COO (首席运营官) - 协调与监督

职责：
- 将 CEO 的决策拆解为执行计划
- 向 CHRO 申请执行 Agent
- 协调 Agent 并行执行
- 监控执行进度
- 汇总结果向 CEO 汇报
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class SubTaskStatus(str, Enum):
    """子任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SubTask:
    """子任务"""
    id: str
    description: str
    agent_type: str  # 需要的 Agent 类型
    dependencies: list[str] = field(default_factory=list)  # 依赖的其他子任务 ID
    priority: int = 0  # 优先级，数字越大越优先
    context: dict = field(default_factory=dict)  # 任务上下文
    status: SubTaskStatus = SubTaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @classmethod
    def create(cls, description: str, agent_type: str, **kwargs) -> "SubTask":
        return cls(
            id=f"subtask_{uuid.uuid4().hex[:8]}",
            description=description,
            agent_type=agent_type,
            **kwargs
        )


@dataclass
class ExecutionPlan:
    """执行计划"""
    id: str
    task_id: str  # 原始任务 ID
    subtasks: list[SubTask]
    parallel_groups: list[list[str]]  # 可并行执行的子任务组
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def create(cls, task_id: str, subtasks: list[SubTask]) -> "ExecutionPlan":
        """创建执行计划，自动分析并行组"""
        plan = cls(
            id=f"plan_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            subtasks=subtasks,
            parallel_groups=[]
        )
        plan._analyze_parallel_groups()
        return plan

    def _analyze_parallel_groups(self):
        """分析哪些任务可以并行执行"""
        completed_ids = set()
        remaining = {st.id: st for st in self.subtasks}
        self.parallel_groups = []

        while remaining:
            # 找出所有依赖已满足的任务
            ready = []
            for task_id, task in remaining.items():
                if all(dep in completed_ids for dep in task.dependencies):
                    ready.append(task_id)

            if not ready:
                # 有循环依赖或错误，强制执行剩余任务
                ready = list(remaining.keys())

            # 按优先级排序
            ready.sort(key=lambda tid: remaining[tid].priority, reverse=True)
            self.parallel_groups.append(ready)

            # 标记为已完成
            for task_id in ready:
                completed_ids.add(task_id)
                del remaining[task_id]


@dataclass
class ExecutionProgress:
    """执行进度"""
    plan_id: str
    total_subtasks: int
    completed: int
    failed: int
    running: int
    pending: int
    current_group: int
    total_groups: int
    estimated_progress: float  # 0-1


@dataclass
class ExecutionResult:
    """执行结果"""
    plan_id: str
    task_id: str
    success: bool
    subtask_results: dict[str, Any]
    summary: str
    started_at: str
    completed_at: str
    total_duration_seconds: float


class COO:
    """首席运营官 - 协调执行层"""

    def __init__(
        self,
        chro=None,
        agent_pool=None,
        llm_provider=None,
        hook_manager=None,
        max_parallel_agents: int = 5,
        timeout_seconds: int = 300
    ):
        self.chro = chro
        self.agent_pool = agent_pool
        self.llm = llm_provider
        self.hook_manager = hook_manager
        self.max_parallel_agents = max_parallel_agents
        self.timeout_seconds = timeout_seconds

        # 执行状态
        self._current_plan: Optional[ExecutionPlan] = None
        self._execution_log: list[dict] = []

    async def plan_execution(self, decision: dict) -> ExecutionPlan:
        """将决策拆解为执行计划"""
        task_id = decision.get("task_id", f"task_{uuid.uuid4().hex[:8]}")
        task_description = decision.get("description", "")
        action_items = decision.get("action_items", [])

        # 如果有 LLM，用 AI 智能拆解
        if self.llm and not action_items:
            action_items = await self._ai_decompose(task_description)

        # 转换为子任务
        subtasks = []
        for i, item in enumerate(action_items):
            if isinstance(item, str):
                # 简单字符串，自动推断 agent 类型
                agent_type = self._infer_agent_type(item)
                subtask = SubTask.create(
                    description=item,
                    agent_type=agent_type,
                    priority=len(action_items) - i  # 先出现的优先级高
                )
            elif isinstance(item, dict):
                # 结构化定义
                subtask = SubTask.create(
                    description=item.get("description", ""),
                    agent_type=item.get("agent_type", "general"),
                    dependencies=item.get("dependencies", []),
                    priority=item.get("priority", 0),
                    context=item.get("context", {})
                )
            else:
                continue

            subtasks.append(subtask)

        plan = ExecutionPlan.create(task_id, subtasks)
        self._current_plan = plan

        return plan

    async def _ai_decompose(self, task_description: str) -> list[dict]:
        """用 AI 智能拆解任务"""
        prompt = f"""将以下任务拆解为具体的执行步骤。

任务：{task_description}

可用的执行者类型：
- researcher: 搜索和调研
- analyst: 数据分析
- writer: 文案撰写
- engineer: 技术实现
- designer: 设计相关
- reviewer: 审核校验

返回 JSON 格式：
[
  {{"description": "步骤描述", "agent_type": "执行者类型", "dependencies": []}}
]

注意：
1. 步骤要具体可执行
2. 标明依赖关系（如果步骤 B 依赖步骤 A 的结果，B 的 dependencies 要包含 A 的索引）
3. 尽量让无依赖的步骤可以并行

只返回 JSON，不要其他内容。"""

        try:
            import json
            response = await self.llm.chat([{"role": "user", "content": prompt}])
            return json.loads(response)
        except Exception as e:
            print(f"AI 拆解任务失败: {e}")
            return [{"description": task_description, "agent_type": "general"}]

    def _infer_agent_type(self, description: str) -> str:
        """根据描述推断 Agent 类型"""
        desc_lower = description.lower()

        keywords_map = {
            "researcher": ["搜索", "调研", "查找", "研究", "search", "research"],
            "analyst": ["分析", "数据", "统计", "趋势", "analyze", "data"],
            "writer": ["撰写", "写作", "文案", "内容", "write", "content"],
            "engineer": ["开发", "代码", "实现", "技术", "code", "implement"],
            "designer": ["设计", "UI", "界面", "视觉", "design"],
            "reviewer": ["审核", "检查", "校验", "review", "check"],
        }

        for agent_type, keywords in keywords_map.items():
            if any(kw in desc_lower for kw in keywords):
                return agent_type

        return "general"

    async def coordinate_agents(self, plan: ExecutionPlan) -> ExecutionResult:
        """协调 Agent 并行执行"""
        start_time = datetime.now()

        # 触发 pre_task hook
        if self.hook_manager:
            await self.hook_manager.trigger("pre_task", {"plan": plan})

        subtask_results = {}
        success = True

        try:
            # 按组执行（组内并行，组间串行）
            for group_idx, group_ids in enumerate(plan.parallel_groups):
                group_subtasks = [
                    st for st in plan.subtasks if st.id in group_ids
                ]

                # 并行执行本组任务
                group_results = await self._execute_group(group_subtasks, plan)

                # 收集结果
                for subtask_id, result in group_results.items():
                    subtask_results[subtask_id] = result
                    subtask = next(st for st in plan.subtasks if st.id == subtask_id)
                    if subtask.status == SubTaskStatus.FAILED:
                        success = False

                # 触发进度 hook
                if self.hook_manager:
                    progress = self.get_progress(plan)
                    await self.hook_manager.trigger("on_progress", {"progress": progress})

        except Exception as e:
            success = False
            if self.hook_manager:
                await self.hook_manager.trigger("on_error", {"error": str(e), "plan": plan})

        end_time = datetime.now()

        # 生成汇总
        summary = await self._generate_summary(plan, subtask_results, success)

        result = ExecutionResult(
            plan_id=plan.id,
            task_id=plan.task_id,
            success=success,
            subtask_results=subtask_results,
            summary=summary,
            started_at=start_time.isoformat(),
            completed_at=end_time.isoformat(),
            total_duration_seconds=(end_time - start_time).total_seconds()
        )

        # 触发 post_task hook
        if self.hook_manager:
            await self.hook_manager.trigger("post_task", {"result": result})

        return result

    async def _execute_group(
        self,
        subtasks: list[SubTask],
        plan: ExecutionPlan
    ) -> dict[str, Any]:
        """并行执行一组子任务"""
        results = {}

        # 限制并行数量
        semaphore = asyncio.Semaphore(self.max_parallel_agents)

        async def execute_one(subtask: SubTask) -> tuple[str, Any]:
            async with semaphore:
                subtask.status = SubTaskStatus.RUNNING
                subtask.started_at = datetime.now().isoformat()

                try:
                    # 从 CHRO 获取 Agent
                    if self.chro:
                        agents = await self.chro.hire_for_task([subtask.agent_type])
                        agent = agents[0] if agents else None
                    elif self.agent_pool:
                        agent = self.agent_pool.get_agent(subtask.agent_type)
                    else:
                        agent = None

                    # 执行任务
                    if agent:
                        result = await asyncio.wait_for(
                            agent.execute(subtask),
                            timeout=self.timeout_seconds
                        )
                    else:
                        # 没有 agent，返回模拟结果
                        result = f"[模拟执行] {subtask.description}"

                    subtask.status = SubTaskStatus.COMPLETED
                    subtask.result = result
                    subtask.completed_at = datetime.now().isoformat()

                    return subtask.id, result

                except asyncio.TimeoutError:
                    subtask.status = SubTaskStatus.FAILED
                    subtask.error = "执行超时"
                    subtask.completed_at = datetime.now().isoformat()
                    return subtask.id, {"error": "执行超时"}

                except Exception as e:
                    subtask.status = SubTaskStatus.FAILED
                    subtask.error = str(e)
                    subtask.completed_at = datetime.now().isoformat()
                    return subtask.id, {"error": str(e)}

        # 并行执行
        tasks = [execute_one(st) for st in subtasks]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, tuple):
                subtask_id, result = item
                results[subtask_id] = result
            elif isinstance(item, Exception):
                print(f"子任务执行异常: {item}")

        return results

    def get_progress(self, plan: ExecutionPlan = None) -> ExecutionProgress:
        """获取执行进度"""
        plan = plan or self._current_plan
        if not plan:
            return None

        completed = len([st for st in plan.subtasks if st.status == SubTaskStatus.COMPLETED])
        failed = len([st for st in plan.subtasks if st.status == SubTaskStatus.FAILED])
        running = len([st for st in plan.subtasks if st.status == SubTaskStatus.RUNNING])
        pending = len([st for st in plan.subtasks if st.status == SubTaskStatus.PENDING])

        # 计算当前组
        current_group = 0
        for i, group_ids in enumerate(plan.parallel_groups):
            group_subtasks = [st for st in plan.subtasks if st.id in group_ids]
            if any(st.status in (SubTaskStatus.PENDING, SubTaskStatus.RUNNING) for st in group_subtasks):
                current_group = i
                break
            current_group = i + 1

        return ExecutionProgress(
            plan_id=plan.id,
            total_subtasks=len(plan.subtasks),
            completed=completed,
            failed=failed,
            running=running,
            pending=pending,
            current_group=current_group,
            total_groups=len(plan.parallel_groups),
            estimated_progress=(completed + failed) / len(plan.subtasks) if plan.subtasks else 0
        )

    async def _generate_summary(
        self,
        plan: ExecutionPlan,
        results: dict[str, Any],
        success: bool
    ) -> str:
        """生成执行汇总"""
        if not self.llm:
            completed = len([st for st in plan.subtasks if st.status == SubTaskStatus.COMPLETED])
            failed = len([st for st in plan.subtasks if st.status == SubTaskStatus.FAILED])
            return f"执行完成: {completed} 成功, {failed} 失败"

        results_text = "\n".join([
            f"- {st.description}: {'成功' if st.status == SubTaskStatus.COMPLETED else '失败'}"
            for st in plan.subtasks
        ])

        prompt = f"""汇总以下任务执行结果，生成简洁的报告（100字以内）：

执行结果：
{results_text}

整体状态：{'成功' if success else '部分失败'}

直接输出汇总，不要其他内容。"""

        try:
            return await self.llm.chat([{"role": "user", "content": prompt}])
        except:
            return f"执行{'成功' if success else '部分失败'}"

    async def aggregate_results(self, result: ExecutionResult) -> dict:
        """汇总执行结果，准备向 CEO 汇报"""
        return {
            "task_id": result.task_id,
            "success": result.success,
            "summary": result.summary,
            "duration_seconds": result.total_duration_seconds,
            "details": result.subtask_results
        }
