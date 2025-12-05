"""CEO Agent - 需求挖掘 + 规划"""
import os
from pathlib import Path
from typing import Optional
from ..core.llm import LLMProvider, create_llm_provider
from ..core.message import Message


class CEO:
    """CEO Agent

    职责：
    - 需求挖掘（框架→提问→发散→收敛）
    - 规划
    - 过程监督
    - 最终验收
    """

    def __init__(self, llm: Optional[LLMProvider] = None):
        self.llm = llm or create_llm_provider()
        self.conversation_history: list[dict] = []
        self.system_prompt = self._load_prompt()
        self.state = "idle"  # idle, exploring, planning, executing, reviewing
        self.current_plan: Optional[dict] = None

    def _load_prompt(self) -> str:
        """加载CEO的prompt模板"""
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "ceo.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return "你是一家AI公司的CEO，帮助用户把想法变成可执行的计划。"

    def _build_messages(self, user_input: str) -> list[dict]:
        """构建发送给LLM的消息"""
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_input})
        return messages

    async def chat(self, user_input: str) -> str:
        """与用户对话"""
        # 更新状态
        if self.state == "idle":
            self.state = "exploring"

        # 构建消息并调用LLM
        messages = self._build_messages(user_input)
        response = await self.llm.chat(messages)

        # 保存对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": response})

        # 检查是否产出了计划
        if '"status": "ready_to_execute"' in response:
            self.state = "planning"
            # TODO: 解析计划并保存到 self.current_plan

        return response

    async def stream_chat(self, user_input: str):
        """流式对话（用于实时显示）"""
        if self.state == "idle":
            self.state = "exploring"

        messages = self._build_messages(user_input)
        full_response = ""

        async for chunk in self.llm.stream_chat(messages):
            full_response += chunk
            yield chunk

        # 保存对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": full_response})

    def reset(self):
        """重置对话"""
        self.conversation_history = []
        self.state = "idle"
        self.current_plan = None

    def get_state(self) -> dict:
        """获取当前状态"""
        return {
            "state": self.state,
            "history_length": len(self.conversation_history),
            "has_plan": self.current_plan is not None
        }
