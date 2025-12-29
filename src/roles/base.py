"""Agent基类"""
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from ..core.company import Company
    from ..core.message import Message


class BaseAgent(ABC):
    """所有Agent的基类"""

    def __init__(self, agent_id: str, name: str, company: "Company"):
        self.id = agent_id
        self.name = name
        self.company = company
        self.llm = company.llm
        self.conversation_history: list[dict] = []
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        """加载prompt模板"""
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / f"{self.id}.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return f"你是{self.name}。"

    def _build_messages(self, user_input: str) -> list[dict]:
        """构建发送给LLM的消息"""
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_input})
        return messages

    async def think(self, input_text: str) -> str:
        """思考并回复"""
        messages = self._build_messages(input_text)
        response = await self.llm.chat(messages)

        # 保存对话历史
        self.conversation_history.append({"role": "user", "content": input_text})
        self.conversation_history.append({"role": "assistant", "content": response})

        return response

    async def send(self, to_agent: str, content: str, msg_type: str = "chat"):
        """发送消息给其他agent"""
        await self.company.send_to(to_agent, content, self.id, msg_type)

    async def broadcast(self, content: str, msg_type: str = "announcement"):
        """广播消息"""
        await self.company.broadcast(content, self.id, msg_type)

    @abstractmethod
    async def handle_message(self, message: "Message"):
        """处理收到的消息 - 子类必须实现"""
        pass

    def reset(self):
        """重置对话历史"""
        self.conversation_history = []

    def save_state(self):
        """保存状态到持久化存储"""
        self.company.save_agent_state(
            self.id,
            state="idle",
            conversation_history=self.conversation_history
        )

    def restore_state(self) -> bool:
        """从持久化存储恢复状态，返回是否成功恢复"""
        state_data = self.company.load_agent_state(self.id)
        if state_data:
            self.conversation_history = state_data.get("conversation_history", [])
            return True
        return False
