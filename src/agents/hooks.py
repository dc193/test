"""HookManager - 钩子系统

借鉴 Oh My OpenCode 的扩展点设计：
- 任务生命周期钩子
- Agent 执行钩子
- 自定义扩展点
- 异步钩子支持
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Any, Optional
from enum import Enum
import asyncio
import uuid


class HookType(str, Enum):
    """钩子类型"""
    # 任务生命周期
    PRE_TASK = "pre_task"           # 任务开始前
    POST_TASK = "post_task"         # 任务完成后
    ON_ERROR = "on_error"           # 任务出错时
    ON_PROGRESS = "on_progress"     # 进度更新时

    # Agent 生命周期
    PRE_AGENT = "pre_agent"         # Agent 执行前
    POST_AGENT = "post_agent"       # Agent 执行后
    AGENT_ERROR = "agent_error"     # Agent 出错时

    # 决策相关
    PRE_DECISION = "pre_decision"   # 决策前
    POST_DECISION = "post_decision" # 决策后

    # 进化相关
    PRE_EVOLUTION = "pre_evolution"   # 进化前
    POST_EVOLUTION = "post_evolution" # 进化后

    # 上下文相关
    CONTEXT_OVERFLOW = "context_overflow"  # 上下文溢出警告
    TOKEN_WARNING = "token_warning"        # Token 使用警告


@dataclass
class HookDefinition:
    """钩子定义"""
    id: str
    hook_type: HookType
    handler: Callable
    name: str = ""
    description: str = ""
    priority: int = 0  # 优先级，数字越大越先执行
    enabled: bool = True
    async_handler: bool = True  # 是否是异步处理器
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class HookResult:
    """钩子执行结果"""
    hook_id: str
    hook_type: HookType
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0


class HookManager:
    """钩子管理器

    功能：
    - 注册和管理钩子
    - 按优先级触发钩子
    - 支持同步和异步钩子
    - 钩子执行结果收集
    """

    def __init__(self):
        self._hooks: dict[HookType, list[HookDefinition]] = {}
        self._execution_log: list[HookResult] = []

    def register(
        self,
        hook_type: HookType,
        handler: Callable,
        name: str = "",
        description: str = "",
        priority: int = 0,
        async_handler: bool = True
    ) -> str:
        """注册钩子"""
        hook = HookDefinition(
            id=f"hook_{uuid.uuid4().hex[:8]}",
            hook_type=hook_type,
            handler=handler,
            name=name or f"{hook_type.value}_handler",
            description=description,
            priority=priority,
            async_handler=async_handler
        )

        if hook_type not in self._hooks:
            self._hooks[hook_type] = []

        self._hooks[hook_type].append(hook)
        # 按优先级排序（高优先级在前）
        self._hooks[hook_type].sort(key=lambda h: h.priority, reverse=True)

        return hook.id

    def unregister(self, hook_id: str) -> bool:
        """注销钩子"""
        for hook_type in self._hooks:
            for i, hook in enumerate(self._hooks[hook_type]):
                if hook.id == hook_id:
                    self._hooks[hook_type].pop(i)
                    return True
        return False

    def enable(self, hook_id: str) -> bool:
        """启用钩子"""
        return self._set_enabled(hook_id, True)

    def disable(self, hook_id: str) -> bool:
        """禁用钩子"""
        return self._set_enabled(hook_id, False)

    def _set_enabled(self, hook_id: str, enabled: bool) -> bool:
        """设置钩子启用状态"""
        for hooks in self._hooks.values():
            for hook in hooks:
                if hook.id == hook_id:
                    hook.enabled = enabled
                    return True
        return False

    async def trigger(
        self,
        hook_type: HookType | str,
        context: dict = None,
        stop_on_error: bool = False
    ) -> list[HookResult]:
        """触发钩子

        Args:
            hook_type: 钩子类型
            context: 传递给钩子的上下文
            stop_on_error: 出错时是否停止执行后续钩子

        Returns:
            所有钩子的执行结果
        """
        # 支持字符串类型
        if isinstance(hook_type, str):
            try:
                hook_type = HookType(hook_type)
            except ValueError:
                return []

        hooks = self._hooks.get(hook_type, [])
        results = []
        context = context or {}

        for hook in hooks:
            if not hook.enabled:
                continue

            start_time = datetime.now()
            result = HookResult(
                hook_id=hook.id,
                hook_type=hook_type,
                success=False
            )

            try:
                if hook.async_handler:
                    if asyncio.iscoroutinefunction(hook.handler):
                        hook_result = await hook.handler(context)
                    else:
                        # 同步函数包装为异步
                        hook_result = await asyncio.to_thread(hook.handler, context)
                else:
                    hook_result = hook.handler(context)

                result.success = True
                result.result = hook_result

            except Exception as e:
                result.success = False
                result.error = str(e)

                if stop_on_error:
                    results.append(result)
                    break

            finally:
                end_time = datetime.now()
                result.duration_ms = (end_time - start_time).total_seconds() * 1000

            results.append(result)
            self._execution_log.append(result)

        # 限制日志大小
        if len(self._execution_log) > 1000:
            self._execution_log = self._execution_log[-500:]

        return results

    def get_hooks(self, hook_type: HookType = None) -> list[HookDefinition]:
        """获取钩子列表"""
        if hook_type:
            return self._hooks.get(hook_type, [])
        return [h for hooks in self._hooks.values() for h in hooks]

    def get_execution_log(
        self,
        hook_type: HookType = None,
        limit: int = 100
    ) -> list[HookResult]:
        """获取执行日志"""
        logs = self._execution_log
        if hook_type:
            logs = [r for r in logs if r.hook_type == hook_type]
        return logs[-limit:]

    def clear_logs(self):
        """清除执行日志"""
        self._execution_log.clear()


# 预定义钩子装饰器
def hook(
    hook_type: HookType,
    name: str = "",
    priority: int = 0
):
    """钩子装饰器

    用法：
    @hook(HookType.PRE_TASK, name="日志记录", priority=10)
    async def log_task_start(context):
        print(f"任务开始: {context.get('task_id')}")
    """
    def decorator(func):
        func._hook_type = hook_type
        func._hook_name = name
        func._hook_priority = priority
        return func
    return decorator


class HookRegistry:
    """钩子注册表 - 用于自动发现和注册钩子"""

    def __init__(self, manager: HookManager):
        self.manager = manager
        self._registered_modules = set()

    def register_module(self, module) -> int:
        """注册模块中的所有钩子"""
        count = 0
        for name in dir(module):
            obj = getattr(module, name)
            if callable(obj) and hasattr(obj, '_hook_type'):
                self.manager.register(
                    hook_type=obj._hook_type,
                    handler=obj,
                    name=obj._hook_name or name,
                    priority=getattr(obj, '_hook_priority', 0)
                )
                count += 1
        self._registered_modules.add(module.__name__)
        return count

    def register_class(self, instance) -> int:
        """注册类实例中的所有钩子"""
        count = 0
        for name in dir(instance):
            if name.startswith('_'):
                continue
            method = getattr(instance, name)
            if callable(method) and hasattr(method, '_hook_type'):
                self.manager.register(
                    hook_type=method._hook_type,
                    handler=method,
                    name=method._hook_name or name,
                    priority=getattr(method, '_hook_priority', 0)
                )
                count += 1
        return count


# 常用钩子示例
class CommonHooks:
    """常用钩子集合"""

    @hook(HookType.PRE_TASK, name="任务日志", priority=100)
    async def log_task_start(context: dict):
        """记录任务开始"""
        task_id = context.get('task_id', 'unknown')
        print(f"[Hook] 任务开始: {task_id}")
        return {"logged": True}

    @hook(HookType.POST_TASK, name="任务完成日志", priority=100)
    async def log_task_end(context: dict):
        """记录任务完成"""
        task_id = context.get('task_id', 'unknown')
        success = context.get('success', False)
        status = "成功" if success else "失败"
        print(f"[Hook] 任务{status}: {task_id}")
        return {"logged": True}

    @hook(HookType.ON_ERROR, name="错误通知", priority=50)
    async def notify_error(context: dict):
        """错误通知"""
        error = context.get('error', 'unknown error')
        print(f"[Hook] 错误: {error}")
        return {"notified": True}

    @hook(HookType.TOKEN_WARNING, name="Token警告", priority=100)
    async def token_warning(context: dict):
        """Token 使用警告"""
        usage = context.get('usage', 0)
        limit = context.get('limit', 0)
        percentage = (usage / limit * 100) if limit > 0 else 0
        print(f"[Hook] Token 警告: {usage}/{limit} ({percentage:.1f}%)")
        return {"warned": True}

    @hook(HookType.CONTEXT_OVERFLOW, name="上下文溢出", priority=100)
    async def context_overflow(context: dict):
        """上下文溢出处理"""
        print(f"[Hook] 上下文溢出警告，建议压缩")
        return {"action": "compress_suggested"}
