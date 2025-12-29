"""AgentPool - Agent 并行执行池

借鉴 Oh My OpenCode 的执行层技巧：
- 并行 Agent 管理
- 资源限制和调度
- 执行状态追踪
- 多模型策略支持
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Callable
from enum import Enum
import uuid


class AgentStatus(str, Enum):
    """Agent 状态"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class AgentInstance:
    """Agent 实例"""
    id: str
    agent_type: str
    agent: Any  # ExecutionAgent 实例
    status: AgentStatus = AgentStatus.IDLE
    current_task_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used_at: Optional[str] = None
    total_tasks: int = 0
    failed_tasks: int = 0


@dataclass
class PoolStats:
    """池统计"""
    total_agents: int
    idle_agents: int
    busy_agents: int
    error_agents: int
    queued_tasks: int
    completed_tasks: int
    failed_tasks: int


class AgentPool:
    """Agent 并行执行池

    功能：
    - 管理多个 Agent 实例
    - 支持并行执行控制
    - 自动扩缩容（在限制范围内）
    - 任务队列管理
    """

    def __init__(
        self,
        max_agents: int = 10,
        max_agents_per_type: int = 3,
        agent_factory: Callable = None,
        llm_provider=None
    ):
        self.max_agents = max_agents
        self.max_agents_per_type = max_agents_per_type
        self.agent_factory = agent_factory
        self.llm = llm_provider

        # Agent 池
        self._agents: dict[str, AgentInstance] = {}
        self._agents_by_type: dict[str, list[str]] = {}

        # 任务队列
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._pending_tasks: dict[str, dict] = {}

        # 统计
        self._completed_tasks = 0
        self._failed_tasks = 0

        # 并发控制
        self._semaphore = asyncio.Semaphore(max_agents)
        self._lock = asyncio.Lock()

    def get_agent(self, agent_type: str) -> Optional[Any]:
        """获取指定类型的 Agent（同步方式，用于简单场景）"""
        # 查找空闲的同类型 Agent
        if agent_type in self._agents_by_type:
            for agent_id in self._agents_by_type[agent_type]:
                instance = self._agents.get(agent_id)
                if instance and instance.status == AgentStatus.IDLE:
                    return instance.agent

        # 创建新 Agent
        instance = self._create_agent(agent_type)
        if instance:
            return instance.agent

        return None

    async def acquire_agent(self, agent_type: str, task_id: str = None) -> Optional[Any]:
        """获取 Agent（异步方式，支持等待）"""
        async with self._semaphore:
            async with self._lock:
                # 查找空闲 Agent
                agent = self._find_idle_agent(agent_type)
                if agent:
                    instance = self._get_instance_by_agent(agent)
                    if instance:
                        instance.status = AgentStatus.BUSY
                        instance.current_task_id = task_id
                        instance.last_used_at = datetime.now().isoformat()
                    return agent

                # 创建新 Agent
                instance = self._create_agent(agent_type)
                if instance:
                    instance.status = AgentStatus.BUSY
                    instance.current_task_id = task_id
                    instance.last_used_at = datetime.now().isoformat()
                    return instance.agent

                return None

    def release_agent(self, agent: Any, success: bool = True):
        """释放 Agent"""
        instance = self._get_instance_by_agent(agent)
        if instance:
            instance.status = AgentStatus.IDLE
            instance.current_task_id = None
            instance.total_tasks += 1
            if not success:
                instance.failed_tasks += 1

    def _find_idle_agent(self, agent_type: str) -> Optional[Any]:
        """查找空闲 Agent"""
        if agent_type in self._agents_by_type:
            for agent_id in self._agents_by_type[agent_type]:
                instance = self._agents.get(agent_id)
                if instance and instance.status == AgentStatus.IDLE:
                    return instance.agent
        return None

    def _create_agent(self, agent_type: str) -> Optional[AgentInstance]:
        """创建新 Agent"""
        # 检查总数限制
        if len(self._agents) >= self.max_agents:
            return None

        # 检查类型限制
        type_count = len(self._agents_by_type.get(agent_type, []))
        if type_count >= self.max_agents_per_type:
            return None

        # 创建 Agent
        if self.agent_factory:
            agent = self.agent_factory(agent_type)
        else:
            agent = self._default_agent_factory(agent_type)

        if not agent:
            return None

        # 创建实例记录
        instance = AgentInstance(
            id=f"agent_{uuid.uuid4().hex[:8]}",
            agent_type=agent_type,
            agent=agent
        )

        # 注册
        self._agents[instance.id] = instance
        if agent_type not in self._agents_by_type:
            self._agents_by_type[agent_type] = []
        self._agents_by_type[agent_type].append(instance.id)

        return instance

    def _default_agent_factory(self, agent_type: str) -> Any:
        """默认 Agent 工厂"""
        from .execution_agent import ExecutionAgent
        return ExecutionAgent(
            agent_type=agent_type,
            llm_provider=self.llm
        )

    def _get_instance_by_agent(self, agent: Any) -> Optional[AgentInstance]:
        """根据 Agent 获取实例"""
        for instance in self._agents.values():
            if instance.agent is agent:
                return instance
        return None

    async def execute_task(
        self,
        agent_type: str,
        task: Any,
        timeout: float = 300
    ) -> Any:
        """执行单个任务"""
        task_id = getattr(task, 'id', str(uuid.uuid4().hex[:8]))

        agent = await self.acquire_agent(agent_type, task_id)
        if not agent:
            return {"error": f"无法获取 {agent_type} 类型的 Agent"}

        try:
            if hasattr(agent, 'execute'):
                result = await asyncio.wait_for(
                    agent.execute(task),
                    timeout=timeout
                )
            else:
                result = {"error": "Agent 不支持 execute 方法"}

            self._completed_tasks += 1
            self.release_agent(agent, success=True)
            return result

        except asyncio.TimeoutError:
            self._failed_tasks += 1
            self.release_agent(agent, success=False)
            return {"error": "执行超时"}

        except Exception as e:
            self._failed_tasks += 1
            self.release_agent(agent, success=False)
            return {"error": str(e)}

    async def execute_batch(
        self,
        tasks: list[tuple[str, Any]],  # [(agent_type, task), ...]
        timeout: float = 300
    ) -> list[Any]:
        """批量并行执行任务"""
        async def execute_one(agent_type: str, task: Any) -> Any:
            return await self.execute_task(agent_type, task, timeout)

        # 并行执行所有任务
        coroutines = [execute_one(at, t) for at, t in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # 处理异常
        processed = []
        for r in results:
            if isinstance(r, Exception):
                processed.append({"error": str(r)})
            else:
                processed.append(r)

        return processed

    def get_stats(self) -> PoolStats:
        """获取池统计"""
        idle = sum(1 for a in self._agents.values() if a.status == AgentStatus.IDLE)
        busy = sum(1 for a in self._agents.values() if a.status == AgentStatus.BUSY)
        error = sum(1 for a in self._agents.values() if a.status == AgentStatus.ERROR)

        return PoolStats(
            total_agents=len(self._agents),
            idle_agents=idle,
            busy_agents=busy,
            error_agents=error,
            queued_tasks=self._task_queue.qsize(),
            completed_tasks=self._completed_tasks,
            failed_tasks=self._failed_tasks
        )

    def get_agent_types(self) -> dict[str, int]:
        """获取各类型 Agent 数量"""
        return {t: len(ids) for t, ids in self._agents_by_type.items()}

    async def cleanup_idle(self, max_idle_seconds: int = 600):
        """清理长时间空闲的 Agent"""
        now = datetime.now()
        to_remove = []

        for agent_id, instance in self._agents.items():
            if instance.status == AgentStatus.IDLE and instance.last_used_at:
                last_used = datetime.fromisoformat(instance.last_used_at)
                idle_seconds = (now - last_used).total_seconds()
                if idle_seconds > max_idle_seconds:
                    to_remove.append(agent_id)

        for agent_id in to_remove:
            instance = self._agents.pop(agent_id, None)
            if instance:
                agent_type = instance.agent_type
                if agent_type in self._agents_by_type:
                    self._agents_by_type[agent_type].remove(agent_id)

        return len(to_remove)

    def reset(self):
        """重置池"""
        self._agents.clear()
        self._agents_by_type.clear()
        self._completed_tasks = 0
        self._failed_tasks = 0
