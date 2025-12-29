"""ContextManager - 上下文管理与 Token 优化

借鉴 Oh My OpenCode 的上下文管理技巧：
- Token 使用追踪
- 上下文窗口管理（70% 警告）
- 自动压缩策略
- 会话恢复机制
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Callable
from enum import Enum
import json


class CompressionStrategy(str, Enum):
    """压缩策略"""
    NONE = "none"           # 不压缩
    SUMMARY = "summary"     # 摘要压缩
    TRUNCATE = "truncate"   # 截断旧内容
    SELECTIVE = "selective" # 选择性保留
    HYBRID = "hybrid"       # 混合策略


@dataclass
class TokenUsage:
    """Token 使用统计"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0


@dataclass
class ContextWindow:
    """上下文窗口"""
    max_tokens: int
    used_tokens: int = 0
    warning_threshold: float = 0.7  # 70% 警告阈值
    critical_threshold: float = 0.9  # 90% 临界阈值

    @property
    def available_tokens(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)

    @property
    def usage_ratio(self) -> float:
        return self.used_tokens / self.max_tokens if self.max_tokens > 0 else 0

    @property
    def is_warning(self) -> bool:
        return self.usage_ratio >= self.warning_threshold

    @property
    def is_critical(self) -> bool:
        return self.usage_ratio >= self.critical_threshold


@dataclass
class ContextSnapshot:
    """上下文快照（用于恢复）"""
    id: str
    messages: list[dict]
    metadata: dict
    token_count: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ContextManager:
    """上下文管理器

    功能：
    - Token 使用追踪和预测
    - 上下文窗口管理
    - 自动压缩
    - 会话快照和恢复
    """

    # 模型上下文窗口大小
    MODEL_CONTEXT_SIZES = {
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        "gpt-4": 128000,
        "gpt-4-turbo": 128000,
        "gpt-3.5-turbo": 16384,
        "default": 100000
    }

    # Token 成本（每 1M tokens，美元）
    TOKEN_COSTS = {
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "default": {"input": 1.0, "output": 2.0}
    }

    def __init__(
        self,
        model: str = "default",
        max_tokens: int = None,
        warning_threshold: float = 0.7,
        critical_threshold: float = 0.9,
        compression_strategy: CompressionStrategy = CompressionStrategy.HYBRID,
        llm_provider=None,
        hook_manager=None
    ):
        self.model = model
        self.llm = llm_provider
        self.hook_manager = hook_manager
        self.compression_strategy = compression_strategy

        # 确定上下文窗口大小
        if max_tokens:
            self.max_tokens = max_tokens
        else:
            self.max_tokens = self.MODEL_CONTEXT_SIZES.get(
                model, self.MODEL_CONTEXT_SIZES["default"]
            )

        # 上下文窗口
        self.window = ContextWindow(
            max_tokens=self.max_tokens,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold
        )

        # 消息历史
        self._messages: list[dict] = []
        self._system_prompt: Optional[str] = None

        # Token 统计
        self._total_usage = TokenUsage()
        self._session_usage = TokenUsage()

        # 快照
        self._snapshots: list[ContextSnapshot] = []
        self._max_snapshots = 10

    def set_system_prompt(self, prompt: str):
        """设置系统提示"""
        self._system_prompt = prompt
        self._update_token_count()

    def add_message(self, role: str, content: str) -> bool:
        """添加消息"""
        message = {"role": role, "content": content}
        estimated_tokens = self._estimate_tokens(content)

        # 检查是否会溢出
        if self.window.used_tokens + estimated_tokens > self.max_tokens:
            # 触发压缩
            self._auto_compress()

        # 再次检查
        if self.window.used_tokens + estimated_tokens > self.max_tokens:
            return False

        self._messages.append(message)
        self._update_token_count()

        # 检查警告
        self._check_thresholds()

        return True

    def get_messages(self, include_system: bool = True) -> list[dict]:
        """获取消息列表"""
        messages = []
        if include_system and self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        messages.extend(self._messages)
        return messages

    def clear_messages(self):
        """清除消息"""
        self._messages.clear()
        self._update_token_count()

    def _estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数量（简单估算）"""
        # 粗略估算：英文约 4 字符/token，中文约 1.5 字符/token
        # 这里使用保守估算
        if not text:
            return 0

        # 检测中文比例
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(text)

        if total_chars == 0:
            return 0

        chinese_ratio = chinese_chars / total_chars

        # 混合估算
        chinese_tokens = chinese_chars / 1.5
        english_tokens = (total_chars - chinese_chars) / 4

        return int(chinese_tokens + english_tokens)

    def _update_token_count(self):
        """更新 token 计数"""
        total = 0

        if self._system_prompt:
            total += self._estimate_tokens(self._system_prompt)

        for msg in self._messages:
            total += self._estimate_tokens(msg.get("content", ""))
            total += 4  # 消息开销

        self.window.used_tokens = total

    def _check_thresholds(self):
        """检查阈值并触发钩子"""
        if self.hook_manager:
            import asyncio

            if self.window.is_critical:
                asyncio.create_task(
                    self.hook_manager.trigger("context_overflow", {
                        "usage": self.window.used_tokens,
                        "limit": self.max_tokens,
                        "ratio": self.window.usage_ratio
                    })
                )
            elif self.window.is_warning:
                asyncio.create_task(
                    self.hook_manager.trigger("token_warning", {
                        "usage": self.window.used_tokens,
                        "limit": self.max_tokens,
                        "ratio": self.window.usage_ratio
                    })
                )

    def _auto_compress(self):
        """自动压缩上下文"""
        if self.compression_strategy == CompressionStrategy.NONE:
            return

        if self.compression_strategy == CompressionStrategy.TRUNCATE:
            self._truncate_old_messages()
        elif self.compression_strategy == CompressionStrategy.SUMMARY:
            # 需要 LLM 支持
            if self.llm:
                import asyncio
                asyncio.create_task(self._summarize_messages())
            else:
                self._truncate_old_messages()
        elif self.compression_strategy == CompressionStrategy.SELECTIVE:
            self._selective_compress()
        else:  # HYBRID
            self._hybrid_compress()

    def _truncate_old_messages(self, keep_recent: int = 10):
        """截断旧消息"""
        if len(self._messages) > keep_recent:
            self._messages = self._messages[-keep_recent:]
            self._update_token_count()

    async def _summarize_messages(self, keep_recent: int = 5):
        """摘要压缩（需要 LLM）"""
        if not self.llm or len(self._messages) <= keep_recent:
            return

        # 分离要压缩的消息和保留的消息
        to_compress = self._messages[:-keep_recent]
        to_keep = self._messages[-keep_recent:]

        if not to_compress:
            return

        # 生成摘要
        compress_text = "\n".join([
            f"{m['role']}: {m['content'][:500]}"
            for m in to_compress
        ])

        prompt = f"""请将以下对话历史压缩为简洁的摘要（不超过 200 字）：

{compress_text}

只输出摘要，不要其他内容。"""

        try:
            summary = await self.llm.chat([{"role": "user", "content": prompt}])
            summary_msg = {"role": "system", "content": f"[历史摘要] {summary}"}
            self._messages = [summary_msg] + to_keep
            self._update_token_count()
        except Exception as e:
            print(f"摘要压缩失败: {e}")
            self._truncate_old_messages(keep_recent)

    def _selective_compress(self):
        """选择性压缩 - 保留重要消息"""
        if len(self._messages) <= 5:
            return

        # 保留策略：首条 + 最近 5 条 + 包含关键词的消息
        keywords = ["重要", "关键", "必须", "注意", "important", "critical", "must"]

        important = []
        for i, msg in enumerate(self._messages):
            content = msg.get("content", "").lower()
            if any(kw in content for kw in keywords):
                important.append(i)

        # 保留的索引
        keep_indices = set([0])  # 首条
        keep_indices.update(important)  # 重要消息
        keep_indices.update(range(len(self._messages) - 5, len(self._messages)))  # 最近5条

        self._messages = [
            self._messages[i] for i in sorted(keep_indices)
            if i < len(self._messages)
        ]
        self._update_token_count()

    def _hybrid_compress(self):
        """混合压缩策略"""
        # 首先尝试选择性压缩
        self._selective_compress()

        # 如果还是超过阈值，进行截断
        if self.window.usage_ratio > 0.8:
            self._truncate_old_messages(keep_recent=8)

    def create_snapshot(self, snapshot_id: str = None) -> ContextSnapshot:
        """创建快照"""
        import uuid
        snapshot = ContextSnapshot(
            id=snapshot_id or f"snap_{uuid.uuid4().hex[:8]}",
            messages=self._messages.copy(),
            metadata={
                "system_prompt": self._system_prompt,
                "model": self.model
            },
            token_count=self.window.used_tokens
        )

        self._snapshots.append(snapshot)

        # 限制快照数量
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]

        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """恢复快照"""
        for snapshot in self._snapshots:
            if snapshot.id == snapshot_id:
                self._messages = snapshot.messages.copy()
                self._system_prompt = snapshot.metadata.get("system_prompt")
                self._update_token_count()
                return True
        return False

    def get_latest_snapshot(self) -> Optional[ContextSnapshot]:
        """获取最新快照"""
        return self._snapshots[-1] if self._snapshots else None

    def record_usage(self, input_tokens: int, output_tokens: int):
        """记录 token 使用"""
        self._session_usage.input_tokens += input_tokens
        self._session_usage.output_tokens += output_tokens
        self._session_usage.total_tokens += input_tokens + output_tokens

        self._total_usage.input_tokens += input_tokens
        self._total_usage.output_tokens += output_tokens
        self._total_usage.total_tokens += input_tokens + output_tokens

        # 计算成本
        costs = self.TOKEN_COSTS.get(self.model, self.TOKEN_COSTS["default"])
        cost = (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000
        self._session_usage.estimated_cost += cost
        self._total_usage.estimated_cost += cost

    def get_usage(self) -> dict:
        """获取使用统计"""
        return {
            "window": {
                "max_tokens": self.max_tokens,
                "used_tokens": self.window.used_tokens,
                "available_tokens": self.window.available_tokens,
                "usage_ratio": f"{self.window.usage_ratio:.1%}",
                "is_warning": self.window.is_warning,
                "is_critical": self.window.is_critical
            },
            "session": {
                "input_tokens": self._session_usage.input_tokens,
                "output_tokens": self._session_usage.output_tokens,
                "total_tokens": self._session_usage.total_tokens,
                "estimated_cost": f"${self._session_usage.estimated_cost:.4f}"
            },
            "total": {
                "input_tokens": self._total_usage.input_tokens,
                "output_tokens": self._total_usage.output_tokens,
                "total_tokens": self._total_usage.total_tokens,
                "estimated_cost": f"${self._total_usage.estimated_cost:.4f}"
            }
        }

    async def optimize(self, context) -> Any:
        """优化执行上下文（供 ExecutionAgent 调用）"""
        # 检查知识上下文大小
        if hasattr(context, 'knowledge_context') and context.knowledge_context:
            knowledge_tokens = self._estimate_tokens(context.knowledge_context)
            if knowledge_tokens > context.max_tokens * 0.3:
                # 知识上下文过大，需要压缩
                context.knowledge_context = context.knowledge_context[:int(context.max_tokens * 0.3 * 2)]

        # 检查任务上下文
        if hasattr(context, 'task_context') and context.task_context:
            context_str = json.dumps(context.task_context, ensure_ascii=False)
            if self._estimate_tokens(context_str) > 2000:
                # 截断任务上下文
                context.task_context = {
                    k: v[:500] if isinstance(v, str) else v
                    for k, v in context.task_context.items()
                }

        return context

    def reset_session(self):
        """重置会话统计"""
        self._session_usage = TokenUsage()
        self.clear_messages()
