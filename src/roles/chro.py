"""CHRO Agent - 找对的人（创建/管理agent）"""
import json
from typing import Optional, TYPE_CHECKING

from .base import BaseAgent
from .worker import Worker, WorkerTemplate
from ..core.message import Message
from ..core.company import AgentStatus, AgentInfo

if TYPE_CHECKING:
    from ..core.company import Company


# 预设的Worker模板
WORKER_TEMPLATES = {
    "researcher": WorkerTemplate(
        id="researcher",
        name="研究员",
        description="负责信息收集、资料整理、背景研究",
        prompt="""你是一名专业研究员，负责：
- 收集和整理相关资料
- 分析信息的可靠性
- 提供研究报告

工作风格：严谨、全面、有条理。输出时注明信息来源。"""
    ),
    "analyst": WorkerTemplate(
        id="analyst",
        name="分析师",
        description="负责数据分析、趋势判断、深度洞察",
        prompt="""你是一名数据分析师，负责：
- 分析数据和趋势
- 提供深度洞察
- 给出可行建议

工作风格：数据驱动、逻辑清晰、结论明确。"""
    ),
    "writer": WorkerTemplate(
        id="writer",
        name="撰写员",
        description="负责文档撰写、报告整理、内容创作",
        prompt="""你是一名专业撰写员，负责：
- 撰写各类文档和报告
- 整理和优化内容结构
- 确保表达清晰准确

工作风格：结构清晰、语言流畅、重点突出。"""
    ),
    "developer": WorkerTemplate(
        id="developer",
        name="开发者",
        description="负责代码编写、技术实现、问题调试",
        prompt="""你是一名软件开发者，负责：
- 编写高质量代码
- 实现技术功能
- 调试和解决问题

工作风格：代码规范、注重可维护性、考虑边界情况。"""
    ),
    "reviewer": WorkerTemplate(
        id="reviewer",
        name="审核员",
        description="负责质量审核、问题检查、反馈建议",
        prompt="""你是一名质量审核员，负责：
- 审核工作成果
- 发现潜在问题
- 提供改进建议

工作风格：细致严谨、客观公正、建设性反馈。"""
    )
}


class CHRO(BaseAgent):
    """CHRO Agent

    职责：
    - 根据计划分析需要什么角色
    - 从模板库创建或动态创建新角色
    - 管理worker agents
    """

    def __init__(self, company: "Company"):
        super().__init__("chro", "CHRO", company)
        self.templates = WORKER_TEMPLATES.copy()
        self.created_workers: dict[str, Worker] = {}

    async def handle_message(self, message: Message):
        """处理收到的消息"""
        # CEO请求组建团队
        if message.from_agent == "ceo" and message.msg_type == "staffing_request":
            await self.handle_staffing_request(message)

        # Worker报告问题
        elif message.msg_type == "worker_issue":
            await self.handle_worker_issue(message)

    async def handle_staffing_request(self, message: Message):
        """处理CEO的组建团队请求"""
        self.company.update_agent_status("chro", AgentStatus.WORKING, "分析人员需求")

        try:
            plan = json.loads(message.content)
        except json.JSONDecodeError:
            plan = {"description": message.content}

        # 分析需要什么角色
        needed_roles = await self.analyze_staffing_needs(plan)

        # 创建workers
        created = []
        for role in needed_roles:
            worker = await self.create_worker(role)
            if worker:
                created.append(worker.name)

        self.company.update_agent_status("chro", AgentStatus.IDLE)

        # 通知CEO团队已组建
        await self.send("ceo", f"团队组建完成，成员：{', '.join(created)}", "team_ready")

        # 通知COO团队成员
        await self.send("coo", json.dumps({
            "workers": [w.id for w in self.created_workers.values()],
            "plan": plan
        }), "team_info")

    async def analyze_staffing_needs(self, plan: dict) -> list[dict]:
        """分析计划需要什么角色"""
        available_templates = "\n".join([
            f"- {t.id}: {t.name} - {t.description}"
            for t in self.templates.values()
        ])

        prompt = f"""分析这个计划需要什么角色：

计划：
{json.dumps(plan, ensure_ascii=False, indent=2)}

可用的角色模板：
{available_templates}

请返回JSON格式的角色列表，每个角色包含：
- template: 模板ID（如果有匹配的）或 "custom"
- name: 角色名称
- custom_prompt: 如果是自定义角色，提供prompt

示例：
```json
[
  {{"template": "researcher", "name": "行业研究员"}},
  {{"template": "analyst", "name": "数据分析师"}},
  {{"template": "custom", "name": "行业专家", "custom_prompt": "你是XX行业的专家..."}}
]
```

只返回JSON，不要其他内容。
"""
        response = await self.think(prompt)

        # 解析返回的角色列表
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        # 默认返回基础团队
        return [
            {"template": "researcher", "name": "研究员"},
            {"template": "analyst", "name": "分析师"},
            {"template": "writer", "name": "撰写员"}
        ]

    async def create_worker(self, role_config: dict) -> Optional[Worker]:
        """创建worker"""
        template_id = role_config.get("template", "custom")
        name = role_config.get("name", template_id)
        worker_id = f"worker_{len(self.created_workers) + 1}"

        if template_id in self.templates:
            template = self.templates[template_id]
            worker = Worker(
                worker_id=worker_id,
                name=name,
                company=self.company,
                template=template
            )
        else:
            # 自定义角色
            custom_template = WorkerTemplate(
                id="custom",
                name=name,
                description=role_config.get("description", "自定义角色"),
                prompt=role_config.get("custom_prompt", f"你是{name}。")
            )
            worker = Worker(
                worker_id=worker_id,
                name=name,
                company=self.company,
                template=custom_template
            )

        # 注册到公司
        self.created_workers[worker_id] = worker
        self.company.register_agent(
            worker_id,
            worker,
            AgentInfo(
                id=worker_id,
                name=name,
                role="worker",
                level=3
            )
        )

        return worker

    async def handle_worker_issue(self, message: Message):
        """处理worker报告的问题"""
        # 分析是否需要创建新角色或替换
        prompt = f"""Worker报告问题：
{message.content}

是否需要：
1. 创建新的专业角色来处理？
2. 替换当前worker？
3. 其他解决方案？

请分析并给出建议。"""
        analysis = await self.think(prompt)

        # 通知COO
        await self.send("coo", f"关于worker问题的分析：\n{analysis}", "staffing_advice")

    def get_workers(self) -> list[dict]:
        """获取所有创建的worker"""
        return [
            {"id": w.id, "name": w.name}
            for w in self.created_workers.values()
        ]
