"""公司核心 - 管理所有agent和通信"""
import asyncio
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from .message import Message
from .llm import LLMProvider, create_llm_provider
from ..memory import KnowledgeBase, create_knowledge_base


class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"


@dataclass
class AgentInfo:
    """Agent信息"""
    id: str
    name: str
    role: str
    level: int  # 1=C-level, 2=组长, 3=执行者
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None


class MessageBus:
    """消息总线 - 所有agent通过这里通信"""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}  # agent_id -> callbacks
        self._type_subscribers: dict[str, list[Callable]] = {}  # msg_type -> callbacks
        self._message_history: list[Message] = []
        self._user_callback: Optional[Callable] = None

    def subscribe(self, agent_id: str, callback: Callable):
        """订阅某个agent的消息"""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = []
        self._subscribers[agent_id].append(callback)

    def subscribe_type(self, msg_type: str, callback: Callable):
        """订阅某类消息"""
        if msg_type not in self._type_subscribers:
            self._type_subscribers[msg_type] = []
        self._type_subscribers[msg_type].append(callback)

    def set_user_callback(self, callback: Callable):
        """设置用户消息回调（用于Web界面显示）"""
        self._user_callback = callback

    async def publish(self, message: Message):
        """发布消息"""
        self._message_history.append(message)

        # 通知用户界面
        if self._user_callback:
            await self._user_callback(message)

        # 点对点消息
        if message.to_agent != "all" and message.to_agent in self._subscribers:
            for callback in self._subscribers[message.to_agent]:
                await callback(message)

        # 广播消息
        if message.to_agent == "all":
            for callbacks in self._subscribers.values():
                for callback in callbacks:
                    await callback(message)

        # 类型订阅
        if message.msg_type in self._type_subscribers:
            for callback in self._type_subscribers[message.msg_type]:
                await callback(message)

    def get_history(self, limit: int = 50) -> list[Message]:
        """获取消息历史"""
        return self._message_history[-limit:]


class Company:
    """AI公司 - 管理所有agent

    God Layer 组成：
    - User: 用户（通过 Web 界面交互）
    - LLM: 可切换的对话模型
    - Memory: 记忆系统
      - memory: 短期/中期记忆（关键词搜索）
      - knowledge_base: 长期知识库（向量搜索）
    """

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        knowledge_base: Optional[KnowledgeBase] = None
    ):
        self.llm = llm or create_llm_provider()
        self.bus = MessageBus()
        self.agents: dict[str, Any] = {}  # agent_id -> agent instance
        self.agent_info: dict[str, AgentInfo] = {}
        self.current_project: Optional[dict] = None
        self.memory = None  # 短期/中期记忆，后续初始化

        # 长期知识库 - 延迟初始化以避免启动时加载模型
        self._knowledge_base = knowledge_base
        self._kb_initialized = knowledge_base is not None

    @property
    def knowledge_base(self) -> KnowledgeBase:
        """获取知识库（延迟初始化）"""
        if not self._kb_initialized:
            self._knowledge_base = create_knowledge_base()
            self._kb_initialized = True
        return self._knowledge_base

    def register_agent(self, agent_id: str, agent: Any, info: AgentInfo):
        """注册agent"""
        self.agents[agent_id] = agent
        self.agent_info[agent_id] = info
        # 订阅消息
        self.bus.subscribe(agent_id, agent.handle_message)

    def get_agent(self, agent_id: str) -> Optional[Any]:
        """获取agent"""
        return self.agents.get(agent_id)

    def get_all_agents(self) -> list[AgentInfo]:
        """获取所有agent信息"""
        return list(self.agent_info.values())

    def update_agent_status(self, agent_id: str, status: AgentStatus, task: Optional[str] = None):
        """更新agent状态"""
        if agent_id in self.agent_info:
            self.agent_info[agent_id].status = status
            self.agent_info[agent_id].current_task = task

    async def broadcast(self, content: str, from_agent: str, msg_type: str = "announcement"):
        """广播消息"""
        message = Message(
            content=content,
            from_agent=from_agent,
            to_agent="all",
            msg_type=msg_type
        )
        await self.bus.publish(message)

    async def send_to(self, to_agent: str, content: str, from_agent: str, msg_type: str = "chat"):
        """发送点对点消息"""
        message = Message(
            content=content,
            from_agent=from_agent,
            to_agent=to_agent,
            msg_type=msg_type
        )
        await self.bus.publish(message)

    def set_project(self, project: dict):
        """设置当前项目"""
        self.current_project = project

    def get_status(self) -> dict:
        """获取公司状态"""
        return {
            "agents": [
                {
                    "id": info.id,
                    "name": info.name,
                    "role": info.role,
                    "level": info.level,
                    "status": info.status.value,
                    "current_task": info.current_task
                }
                for info in self.agent_info.values()
            ],
            "project": self.current_project,
            "message_count": len(self.bus._message_history)
        }
