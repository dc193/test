"""AI 公司智能体系统

三层架构：
- GodLayer: 元认知层，负责观察和进化
- CEOAgent: 执行层，负责任务处理和决策
- AdvisorySystem: 顾问层，提供多元视角建议
"""

from .god_layer import GodLayer
from .ceo_agent import CEOAgent
from .advisory import AdvisorySystem, Perspective

__all__ = [
    "GodLayer",
    "CEOAgent",
    "AdvisorySystem",
    "Perspective"
]
