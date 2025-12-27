"""Knowledge Curator - 知识管家 AI

功能：
- 维护中心思想（用户目标/偏好）
- 审查知识库，发现过时/低质量内容
- 生成淘汰建议，等待用户确认后执行
"""
import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from .knowledge_base import KnowledgeBase, Knowledge, KnowledgeType

if TYPE_CHECKING:
    from ..core.llm import LLMProvider


# 默认中心思想
DEFAULT_CORE_BELIEF = """我是一个软件工程师，专注于构建高质量的软件产品。

我的技术偏好：
- 代码要简洁、可维护
- 架构要清晰、可扩展
- 偏好现代技术栈
- 重视测试和文档

我希望知识库帮我：
- 积累优秀的代码模式和设计经验
- 学习业界最佳实践
- 避免重复犯错
"""


# 审查提示词
REVIEW_PROMPT = """你是一个知识管家 AI，负责审查和管理知识库。

## 用户的中心思想
{core_belief}

## 当前知识库内容
{knowledge_list}

---

请审查这些知识，找出以下问题：

1. **过时内容** - 技术已淘汰、方法已过时
2. **低质量内容** - 信息不准确、描述模糊、价值不高
3. **重复内容** - 与其他知识高度重复
4. **与中心思想不符** - 与用户目标/偏好不匹配

对于每个建议淘汰的知识，请说明：
- 知识 ID
- 淘汰原因
- 建议（删除/保留但需更新/合并到其他知识）

请用 JSON 格式返回，示例：
```json
{{
  "summary": "审查了 X 条知识，建议淘汰 Y 条",
  "recommendations": [
    {{
      "id": "kb_xxx",
      "title": "知识标题",
      "reason": "淘汰原因",
      "suggestion": "delete/update/merge",
      "detail": "具体说明"
    }}
  ],
  "healthy_count": 5,
  "issues_count": 2
}}
```

如果知识库整体健康，没有需要淘汰的内容，返回空的 recommendations 列表。
"""


@dataclass
class ReviewRecommendation:
    """审查建议"""
    id: str
    title: str
    reason: str
    suggestion: str  # delete / update / merge
    detail: str


@dataclass
class ReviewResult:
    """审查结果"""
    summary: str
    recommendations: list[ReviewRecommendation]
    healthy_count: int
    issues_count: int
    reviewed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class KnowledgeCurator:
    """知识管家 - 审查和管理知识库"""

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        llm_provider: Optional["LLMProvider"] = None,
        config_dir: str = "data/curator"
    ):
        self.kb = knowledge_base
        self.llm = llm_provider
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 配置文件
        self.belief_file = self.config_dir / "core_belief.txt"
        self.history_file = self.config_dir / "review_history.json"

    def get_core_belief(self) -> str:
        """获取中心思想"""
        if self.belief_file.exists():
            return self.belief_file.read_text(encoding="utf-8")
        return DEFAULT_CORE_BELIEF

    def set_core_belief(self, belief: str) -> None:
        """设置中心思想"""
        self.belief_file.write_text(belief, encoding="utf-8")

    async def review(self) -> ReviewResult:
        """审查知识库"""
        if self.llm is None:
            raise ValueError("需要 LLM provider 来审查知识库")

        # 获取所有知识
        all_knowledge = list(self.kb._knowledge_meta.values())

        if not all_knowledge:
            return ReviewResult(
                summary="知识库为空，无需审查",
                recommendations=[],
                healthy_count=0,
                issues_count=0
            )

        # 构建知识列表文本
        knowledge_text = ""
        for k in all_knowledge:
            knowledge_text += f"""
---
ID: {k.id}
标题: {k.title}
类型: {k.knowledge_type.value}
来源: {k.source}
创建时间: {k.created_at}
内容摘要: {k.content[:500]}...
---
"""

        # 构建 prompt
        prompt = REVIEW_PROMPT.format(
            core_belief=self.get_core_belief(),
            knowledge_list=knowledge_text
        )

        # 调用 LLM
        messages = [{"role": "user", "content": prompt}]
        response = await self.llm.chat(messages)

        # 解析结果
        try:
            # 提取 JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
            else:
                # 没找到 JSON，返回默认结果
                return ReviewResult(
                    summary="审查完成，知识库整体健康",
                    recommendations=[],
                    healthy_count=len(all_knowledge),
                    issues_count=0
                )

            recommendations = [
                ReviewRecommendation(
                    id=r.get("id", ""),
                    title=r.get("title", ""),
                    reason=r.get("reason", ""),
                    suggestion=r.get("suggestion", "delete"),
                    detail=r.get("detail", "")
                )
                for r in data.get("recommendations", [])
            ]

            result = ReviewResult(
                summary=data.get("summary", "审查完成"),
                recommendations=recommendations,
                healthy_count=data.get("healthy_count", len(all_knowledge) - len(recommendations)),
                issues_count=data.get("issues_count", len(recommendations))
            )

            # 保存审查历史
            self._save_review_history(result)

            return result

        except json.JSONDecodeError:
            return ReviewResult(
                summary="审查完成，但解析结果时出错",
                recommendations=[],
                healthy_count=len(all_knowledge),
                issues_count=0
            )

    def delete_knowledge(self, knowledge_ids: list[str]) -> dict:
        """删除指定的知识"""
        deleted = []
        failed = []

        for kid in knowledge_ids:
            if self.kb.delete(kid):
                deleted.append(kid)
            else:
                failed.append(kid)

        return {
            "deleted": deleted,
            "failed": failed,
            "deleted_count": len(deleted)
        }

    def _save_review_history(self, result: ReviewResult):
        """保存审查历史"""
        history = []
        if self.history_file.exists():
            try:
                history = json.loads(self.history_file.read_text(encoding="utf-8"))
            except:
                pass

        history.append({
            "reviewed_at": result.reviewed_at,
            "summary": result.summary,
            "healthy_count": result.healthy_count,
            "issues_count": result.issues_count,
            "recommendations_count": len(result.recommendations)
        })

        # 只保留最近 20 条
        history = history[-20:]

        self.history_file.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_review_history(self) -> list[dict]:
        """获取审查历史"""
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text(encoding="utf-8"))
            except:
                pass
        return []
