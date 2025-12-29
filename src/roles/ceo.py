"""CEO Agent - 需求挖掘 + 规划 + 监督 + 验收"""
import json
import re
from typing import Optional, TYPE_CHECKING
from pathlib import Path

from .base import BaseAgent
from ..core.message import Message
from ..core.company import AgentStatus

if TYPE_CHECKING:
    from ..core.company import Company


class CEO(BaseAgent):
    """CEO Agent

    职责：
    - 需求挖掘（框架→提问→发散→收敛）
    - 规划
    - 过程监督
    - 最终验收
    """

    def __init__(self, company: "Company"):
        super().__init__("ceo", "CEO", company)
        self.state = "idle"  # idle, exploring, planning, executing, reviewing
        self.current_plan: Optional[dict] = None

    async def handle_message(self, message: Message):
        """处理收到的消息"""
        # 来自COO的警报
        if message.from_agent == "coo" and message.msg_type == "alert":
            response = await self.handle_alert(message)
            await self.send("coo", response, "response")

        # 来自COO的进度报告
        elif message.from_agent == "coo" and message.msg_type == "report":
            await self.handle_progress_report(message)

        # 来自CHRO的团队组建完成
        elif message.from_agent == "chro" and message.msg_type == "team_ready":
            await self.handle_team_ready(message)

    async def handle_alert(self, message: Message) -> str:
        """处理COO发来的警报"""
        prompt = f"""COO发来警报：
{message.content}

请分析这个问题并给出决策：
1. 是否需要调整计划？
2. 是否需要暂停执行？
3. 给COO的指示是什么？
"""
        response = await self.think(prompt)
        return response

    async def handle_progress_report(self, message: Message):
        """处理进度报告"""
        # CEO主动监督：分析进度是否符合预期
        prompt = f"""收到进度报告：
{message.content}

当前计划：
{json.dumps(self.current_plan, ensure_ascii=False, indent=2) if self.current_plan else '暂无'}

请分析：
1. 进度是否符合预期？
2. 是否发现潜在风险？
3. 是否需要介入？
"""
        analysis = await self.think(prompt)

        # 如果需要介入，通知COO
        if "需要介入" in analysis or "风险" in analysis:
            await self.send("coo", analysis, "guidance")

    async def handle_team_ready(self, message: Message):
        """处理团队组建完成"""
        self.state = "executing"
        self.company.update_agent_status("ceo", AgentStatus.WORKING, "监督执行")

        # 通知COO开始执行
        await self.send("coo", f"团队已就位，请开始执行计划：\n{json.dumps(self.current_plan, ensure_ascii=False, indent=2)}", "start_execution")

    async def chat(self, user_input: str) -> str:
        """与用户对话"""
        if self.state == "idle":
            self.state = "exploring"
            self.company.update_agent_status("ceo", AgentStatus.WORKING, "需求探索")

        response = await self.think(user_input)

        # 检查是否产出了计划
        if '"status": "ready_to_execute"' in response:
            self.state = "planning"
            self.current_plan = self._extract_plan(response)
            self.company.update_agent_status("ceo", AgentStatus.WORKING, "计划制定完成")

            # 通知CHRO组建团队
            if self.current_plan:
                await self.send("chro", json.dumps(self.current_plan, ensure_ascii=False), "staffing_request")

        return response

    async def stream_chat(self, user_input: str):
        """流式对话（用于实时显示）"""
        if self.state == "idle":
            self.state = "exploring"
            self.company.update_agent_status("ceo", AgentStatus.WORKING, "需求探索")

        messages = self._build_messages(user_input)
        full_response = ""

        async for chunk in self.llm.stream_chat(messages):
            full_response += chunk
            yield chunk

        # 保存对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": full_response})

        # 检查是否产出了计划
        if '"status": "ready_to_execute"' in full_response:
            self.state = "planning"
            self.current_plan = self._extract_plan(full_response)
            self.company.update_agent_status("ceo", AgentStatus.WORKING, "计划制定完成")

            if self.current_plan:
                await self.send("chro", json.dumps(self.current_plan, ensure_ascii=False), "staffing_request")

        # 自动保存状态
        self.save_state()

    def _extract_plan(self, response: str) -> Optional[dict]:
        """从回复中提取计划JSON"""
        try:
            # 尝试找到JSON块
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # 尝试直接解析
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
        return None

    def reset(self):
        """重置"""
        super().reset()
        self.state = "idle"
        self.current_plan = None
        self.company.update_agent_status("ceo", AgentStatus.IDLE)

    def get_state(self) -> dict:
        """获取当前状态"""
        return {
            "state": self.state,
            "history_length": len(self.conversation_history),
            "has_plan": self.current_plan is not None,
            "plan": self.current_plan
        }

    def save_state(self):
        """保存 CEO 状态到持久化存储"""
        self.company.save_agent_state(
            self.id,
            state=self.state,
            current_plan=self.current_plan,
            conversation_history=self.conversation_history
        )

    def restore_state(self) -> bool:
        """从持久化存储恢复 CEO 状态"""
        state_data = self.company.load_agent_state(self.id)
        if state_data:
            self.state = state_data.get("state", "idle")
            self.current_plan = state_data.get("current_plan")
            self.conversation_history = state_data.get("conversation_history", [])

            # 恢复 AgentStatus
            if self.state == "idle":
                self.company.update_agent_status("ceo", AgentStatus.IDLE)
            else:
                task = "需求探索" if self.state == "exploring" else \
                       "计划制定完成" if self.state == "planning" else \
                       "监督执行" if self.state == "executing" else \
                       "验收审查" if self.state == "reviewing" else None
                self.company.update_agent_status("ceo", AgentStatus.WORKING, task)
            return True
        return False
