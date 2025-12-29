"""执行层 Agent - 实际执行任务的工作者

特点：
- 根据 Profile 定义的能力执行任务
- 支持使用 MCP 外部工具
- 支持调用 Skills 复用流程
- 集成上下文管理和 Token 优化
"""

from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime


@dataclass
class ExecutionContext:
    """执行上下文"""
    task_description: str
    task_context: dict
    available_tools: list[str]
    knowledge_context: str = ""
    max_tokens: int = 4000


class ExecutionAgent:
    """执行层 Agent"""

    def __init__(
        self,
        agent_type: str,
        profile=None,
        llm_provider=None,
        mcp_registry: dict = None,
        skill_registry: dict = None,
        context_manager=None
    ):
        self.agent_type = agent_type
        self.profile = profile
        self.llm = llm_provider
        self.mcp_registry = mcp_registry or {}
        self.skill_registry = skill_registry or {}
        self.context_manager = context_manager

        # 执行统计
        self.total_executions = 0
        self.successful_executions = 0

    async def execute(self, subtask) -> Any:
        """执行子任务"""
        self.total_executions += 1
        start_time = datetime.now()

        try:
            # 构建执行上下文
            context = ExecutionContext(
                task_description=subtask.description,
                task_context=subtask.context,
                available_tools=list(self.mcp_registry.keys())
            )

            # 如果有上下文管理器，优化上下文
            if self.context_manager:
                context = await self.context_manager.optimize(context)

            # 检查是否可以使用 Skill
            skill = self._match_skill(subtask.description)
            if skill:
                result = await self._execute_skill(skill, context)
            else:
                result = await self._execute_with_llm(context)

            self.successful_executions += 1
            return result

        except Exception as e:
            return {"error": str(e), "agent_type": self.agent_type}

    def _match_skill(self, description: str) -> Optional[str]:
        """匹配可复用的 Skill"""
        desc_lower = description.lower()

        skill_keywords = {
            "competitive_analysis": ["竞品", "竞争", "对手", "competitive"],
            "user_research": ["用户调研", "用户研究", "user research"],
            "technical_review": ["技术评审", "代码审查", "tech review"],
            "content_creation": ["内容创作", "文案撰写", "content"],
        }

        for skill_name, keywords in skill_keywords.items():
            if skill_name in self.skill_registry:
                if any(kw in desc_lower for kw in keywords):
                    return skill_name

        return None

    async def _execute_skill(self, skill_name: str, context: ExecutionContext) -> Any:
        """执行预定义 Skill"""
        skill = self.skill_registry.get(skill_name)
        if skill and hasattr(skill, 'execute'):
            return await skill.execute(context)

        # 降级为 LLM 执行
        return await self._execute_with_llm(context)

    async def _execute_with_llm(self, context: ExecutionContext) -> Any:
        """使用 LLM 执行任务"""
        if not self.llm:
            return f"[模拟执行] {context.task_description}"

        # 构建 prompt
        role_prompt = self._get_role_prompt()
        tools_prompt = self._get_tools_prompt(context.available_tools)

        prompt = f"""{role_prompt}

任务：{context.task_description}

{f"上下文：{context.task_context}" if context.task_context else ""}
{f"相关知识：{context.knowledge_context}" if context.knowledge_context else ""}
{tools_prompt}

请完成任务，直接输出结果。"""

        try:
            result = await self.llm.chat([{"role": "user", "content": prompt}])
            return result
        except Exception as e:
            return f"执行失败: {e}"

    def _get_role_prompt(self) -> str:
        """获取角色 prompt"""
        if self.profile:
            return f"你是一个 {self.profile.name}，{self.profile.description}。"

        role_prompts = {
            "researcher": "你是一个调研员，擅长搜索信息、收集资料。",
            "analyst": "你是一个分析师，擅长数据分析、趋势解读。",
            "writer": "你是一个文案，擅长撰写清晰、有说服力的内容。",
            "engineer": "你是一个工程师，擅长技术实现和问题解决。",
            "designer": "你是一个设计师，擅长用户体验和视觉设计。",
            "reviewer": "你是一个审核员，擅长质量检查和合规审核。",
            "general": "你是一个通用助手，能够处理各类任务。",
        }

        return role_prompts.get(self.agent_type, role_prompts["general"])

    def _get_tools_prompt(self, available_tools: list[str]) -> str:
        """获取工具 prompt"""
        if not available_tools:
            return ""

        tools_desc = []
        for tool_name in available_tools:
            mcp = self.mcp_registry.get(tool_name)
            if mcp and hasattr(mcp, 'description'):
                tools_desc.append(f"- {tool_name}: {mcp.description}")
            else:
                tools_desc.append(f"- {tool_name}")

        return f"""
可用工具：
{chr(10).join(tools_desc)}

如果需要使用工具，请在输出中说明。"""

    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        """使用 MCP 工具"""
        mcp = self.mcp_registry.get(tool_name)
        if not mcp:
            return {"error": f"工具 {tool_name} 不存在"}

        if hasattr(mcp, 'execute'):
            return await mcp.execute(**kwargs)
        elif hasattr(mcp, '__call__'):
            return await mcp(**kwargs)
        else:
            return {"error": f"工具 {tool_name} 不可执行"}

    def get_stats(self) -> dict:
        """获取执行统计"""
        return {
            "agent_type": self.agent_type,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "success_rate": (
                self.successful_executions / self.total_executions
                if self.total_executions > 0 else 0
            )
        }
