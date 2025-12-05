"""COO Agent - 协调执行 + 进度监控 + 异常处理"""
import json
import asyncio
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

from .base import BaseAgent
from ..core.message import Message
from ..core.company import AgentStatus

if TYPE_CHECKING:
    from ..core.company import Company


@dataclass
class Task:
    """任务"""
    id: str
    description: str
    assigned_to: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, blocked
    result: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class COO(BaseAgent):
    """COO Agent

    职责：
    - 协调执行：分配任务给workers
    - 进度监控：跟踪任务完成情况
    - 异常处理：发现问题立刻找CEO
    """

    def __init__(self, company: "Company"):
        super().__init__("coo", "COO", company)
        self.current_plan: Optional[dict] = None
        self.workers: list[str] = []
        self.tasks: dict[str, Task] = {}
        self.task_counter = 0

    async def handle_message(self, message: Message):
        """处理收到的消息"""
        # CHRO通知团队信息
        if message.from_agent == "chro" and message.msg_type == "team_info":
            await self.handle_team_info(message)

        # CEO指示开始执行
        elif message.from_agent == "ceo" and message.msg_type == "start_execution":
            await self.start_execution(message)

        # CEO的指导
        elif message.from_agent == "ceo" and message.msg_type == "guidance":
            await self.handle_guidance(message)

        # Worker完成任务
        elif message.msg_type == "task_complete":
            await self.handle_task_complete(message)

        # Worker状态报告
        elif message.msg_type == "status_report":
            await self.handle_status_report(message)

        # CHRO的人员建议
        elif message.from_agent == "chro" and message.msg_type == "staffing_advice":
            await self.handle_staffing_advice(message)

        # 用户介入
        elif message.from_agent == "user":
            await self.handle_user_intervention(message)

    async def handle_team_info(self, message: Message):
        """处理CHRO发来的团队信息"""
        try:
            info = json.loads(message.content)
            self.workers = info.get("workers", [])
            self.current_plan = info.get("plan", {})
        except:
            pass

    async def start_execution(self, message: Message):
        """开始执行计划"""
        self.company.update_agent_status("coo", AgentStatus.WORKING, "协调执行")

        # 解析计划，创建任务
        await self.create_tasks_from_plan()

        # 开始分配任务
        await self.distribute_tasks()

    async def create_tasks_from_plan(self):
        """从计划创建任务"""
        if not self.current_plan:
            return

        # 分析计划，提取任务
        prompt = f"""分析以下计划，提取具体任务：

{json.dumps(self.current_plan, ensure_ascii=False, indent=2)}

请返回JSON格式的任务列表：
```json
[
  {{"description": "任务描述", "priority": "high/medium/low", "depends_on": []}}
]
```

按执行顺序排列，只返回JSON。
"""
        response = await self.think(prompt)

        # 解析任务
        try:
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                task_list = json.loads(json_match.group())
                for task_data in task_list:
                    self.task_counter += 1
                    task_id = f"task_{self.task_counter}"
                    self.tasks[task_id] = Task(
                        id=task_id,
                        description=task_data.get("description", "")
                    )
        except:
            # 如果解析失败，创建一个通用任务
            self.task_counter += 1
            self.tasks[f"task_{self.task_counter}"] = Task(
                id=f"task_{self.task_counter}",
                description=str(self.current_plan)
            )

    async def distribute_tasks(self):
        """分配任务给workers"""
        pending_tasks = [t for t in self.tasks.values() if t.status == "pending"]

        if not pending_tasks or not self.workers:
            return

        # 分析哪个worker适合哪个任务
        for task in pending_tasks:
            if not self.workers:
                break

            # 简单策略：轮流分配
            worker_id = self.workers[0]

            # 分配任务
            task.assigned_to = worker_id
            task.status = "in_progress"

            # 发送任务给worker
            await self.send(worker_id, json.dumps({
                "task_id": task.id,
                "description": task.description
            }), "task")

            # 报告给CEO
            await self.send("ceo", f"任务 {task.id} 已分配给 {worker_id}：{task.description[:50]}...", "report")

    async def handle_task_complete(self, message: Message):
        """处理任务完成"""
        worker_id = message.from_agent

        # 找到该worker的任务
        for task in self.tasks.values():
            if task.assigned_to == worker_id and task.status == "in_progress":
                task.status = "completed"
                task.result = message.content
                task.completed_at = datetime.now()
                break

        # 检查是否所有任务都完成了
        all_completed = all(t.status == "completed" for t in self.tasks.values())

        if all_completed:
            await self.handle_all_tasks_complete()
        else:
            # 继续分配下一个任务
            await self.distribute_tasks()

            # 定期报告进度
            await self.report_progress()

    async def handle_all_tasks_complete(self):
        """所有任务完成"""
        self.company.update_agent_status("coo", AgentStatus.IDLE)

        # 汇总结果
        results = []
        for task in self.tasks.values():
            results.append({
                "task": task.description,
                "result": task.result
            })

        # 报告给CEO
        await self.send("ceo", f"所有任务已完成！\n\n结果汇总：\n{json.dumps(results, ensure_ascii=False, indent=2)}", "report")

        # 广播完成
        await self.broadcast("项目执行完成！", "announcement")

    async def report_progress(self):
        """报告进度"""
        completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        total = len(self.tasks)
        in_progress = sum(1 for t in self.tasks.values() if t.status == "in_progress")

        progress = f"进度: {completed}/{total} 完成, {in_progress} 进行中"
        await self.send("ceo", progress, "report")

    async def handle_guidance(self, message: Message):
        """处理CEO的指导"""
        # 分析CEO的指导并采取行动
        prompt = f"""CEO给出指导：
{message.content}

当前任务状态：
{json.dumps({t.id: t.status for t in self.tasks.values()}, ensure_ascii=False)}

请分析需要采取什么行动。"""
        analysis = await self.think(prompt)

        # 如果需要暂停某些任务
        if "暂停" in message.content.lower():
            for task in self.tasks.values():
                if task.status == "in_progress":
                    task.status = "pending"

    async def handle_status_report(self, message: Message):
        """处理worker状态报告"""
        # 检查是否有问题
        if "问题" in message.content or "blocked" in message.content.lower():
            # 立即报告CEO
            await self.send("ceo", f"Worker报告问题：\n{message.content}", "alert")

    async def handle_staffing_advice(self, message: Message):
        """处理CHRO的人员建议"""
        # 记录建议，必要时调整分配
        pass

    async def handle_user_intervention(self, message: Message):
        """处理用户介入"""
        content = message.content.lower()

        if "暂停" in content or "stop" in content:
            # 暂停所有任务
            for task in self.tasks.values():
                if task.status == "in_progress":
                    task.status = "pending"
            await self.broadcast("收到暂停指令，所有任务已暂停", "announcement")
            await self.send("ceo", "用户请求暂停，已暂停所有进行中的任务", "alert")

        elif "继续" in content or "resume" in content:
            # 继续执行
            await self.distribute_tasks()
            await self.broadcast("继续执行任务", "announcement")

        elif "跳过" in content or "skip" in content:
            # 跳过当前任务
            for task in self.tasks.values():
                if task.status == "in_progress":
                    task.status = "completed"
                    task.result = "用户跳过"
            await self.distribute_tasks()

    def get_progress(self) -> dict:
        """获取进度"""
        completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        total = len(self.tasks)

        return {
            "total_tasks": total,
            "completed": completed,
            "in_progress": sum(1 for t in self.tasks.values() if t.status == "in_progress"),
            "pending": sum(1 for t in self.tasks.values() if t.status == "pending"),
            "progress_percent": (completed / total * 100) if total > 0 else 0,
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description[:50],
                    "status": t.status,
                    "assigned_to": t.assigned_to
                }
                for t in self.tasks.values()
            ]
        }
