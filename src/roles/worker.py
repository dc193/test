"""Worker Agent - 动态创建的执行者"""
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from .base import BaseAgent
from ..core.message import Message
from ..core.company import AgentStatus

if TYPE_CHECKING:
    from ..core.company import Company


@dataclass
class WorkerTemplate:
    """Worker模板"""
    id: str
    name: str
    description: str
    prompt: str


class Worker(BaseAgent):
    """Worker Agent - 动态创建的执行者

    由CHRO根据计划创建，负责具体任务执行
    """

    def __init__(self, worker_id: str, name: str, company: "Company", template: WorkerTemplate):
        self.template = template
        self.worker_id = worker_id
        super().__init__(worker_id, name, company)
        self.current_task: Optional[dict] = None
        self.task_results: list[dict] = []

    def _load_prompt(self) -> str:
        """使用模板的prompt"""
        base_prompt = self.template.prompt

        # 添加通用的工作指南
        return f"""{base_prompt}

## 工作指南

1. 收到任务后，先分析任务要求
2. 执行任务，输出结果
3. 遇到问题时，及时报告给COO
4. 完成后，将结果报告给COO

## 输出格式

任务完成时，使用以下格式：
```
【任务完成】
任务：[任务描述]
结果：[执行结果]
备注：[其他说明]
```

遇到问题时：
```
【遇到问题】
任务：[任务描述]
问题：[问题描述]
建议：[解决建议]
```
"""

    async def handle_message(self, message: Message):
        """处理收到的消息"""
        # COO分配任务
        if message.from_agent == "coo" and message.msg_type == "task":
            await self.handle_task(message)

        # COO询问进度
        elif message.from_agent == "coo" and message.msg_type == "status_check":
            await self.report_status()

        # 其他worker的协作请求
        elif message.msg_type == "collaboration":
            await self.handle_collaboration(message)

    async def handle_task(self, message: Message):
        """处理分配的任务"""
        self.company.update_agent_status(self.id, AgentStatus.WORKING, "执行任务")

        try:
            import json
            self.current_task = json.loads(message.content)
        except:
            self.current_task = {"description": message.content}

        # 执行任务
        result = await self.execute_task(self.current_task)

        # 保存结果
        self.task_results.append({
            "task": self.current_task,
            "result": result
        })

        self.company.update_agent_status(self.id, AgentStatus.IDLE)

        # 报告给COO
        await self.send("coo", result, "task_complete")

    async def execute_task(self, task: dict) -> str:
        """执行任务"""
        task_desc = task.get("description", str(task))

        prompt = f"""请执行以下任务：

{task_desc}

要求：
1. 认真分析任务要求
2. 按照你的专业能力完成任务
3. 输出清晰的结果
"""
        result = await self.think(prompt)
        return result

    async def report_status(self):
        """报告当前状态"""
        status = {
            "worker_id": self.id,
            "name": self.name,
            "current_task": self.current_task,
            "completed_tasks": len(self.task_results)
        }
        await self.send("coo", str(status), "status_report")

    async def handle_collaboration(self, message: Message):
        """处理协作请求"""
        prompt = f"""收到来自 {message.from_agent} 的协作请求：

{message.content}

请分析并回复。如果需要协作，说明你能提供什么帮助。
"""
        response = await self.think(prompt)
        await self.send(message.from_agent, response, "collaboration_response")

    def get_results(self) -> list[dict]:
        """获取所有任务结果"""
        return self.task_results
