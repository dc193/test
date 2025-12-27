"""Content Learner - 从各种内容中学习

支持：
- 从网页文章学习（多页爬取、JS 渲染）
- 从 PDF 学习
- 从文字/想法学习（AI 提炼）
"""
import re
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass

from .knowledge_base import KnowledgeBase, KnowledgeType
from .web_scraper import WebScraper, ScrapedContent

if TYPE_CHECKING:
    from ..core.llm import LLMProvider


@dataclass
class LearningResult:
    """学习结果"""
    success: bool
    title: str = ""
    knowledge_type: str = ""
    analysis: str = ""
    knowledge_id: str = ""
    error: str = ""
    # 抓取信息
    pages_scraped: int = 0
    content_length: int = 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "title": self.title,
            "knowledge_type": self.knowledge_type,
            "analysis": self.analysis,
            "knowledge_id": self.knowledge_id,
            "error": self.error,
            "pages_scraped": self.pages_scraped,
            "content_length": self.content_length
        }


# 文章分析 prompt
ARTICLE_ANALYSIS_PROMPT = """你是一位善于提炼知识的专家。请深度分析以下文章内容，提炼出有价值的知识和洞察。

## 文章内容
{content}

---

请用中文进行深度分析：

## 一、核心观点
1. **文章的核心论点是什么？** 作者想要表达什么？
2. **支撑论据是什么？** 作者用什么来证明自己的观点？
3. **为什么这个观点重要？** 对我有什么意义？

## 二、思维模式
1. **作者是如何思考这个问题的？** 他的思路和逻辑是什么？
2. **有什么独特的视角？** 这篇文章和其他人的观点有什么不同？
3. **这种思维方式可以如何复用？** 我在什么场景下可以用类似的思路？

## 三、行为原则
从文章中提炼出可执行的行为原则：
- **场景**：当遇到XXX情况时
- **原则**：应该XXX
- **原因**：因为XXX

至少提炼 2-3 条原则。

## 四、关键洞察
文章中最有价值的 2-3 个洞察是什么？为什么它们重要？

## 五、我的行动项
读完这篇文章，我应该：
1. 改变什么认知？
2. 采取什么行动？
3. 避免什么误区？

---
请直接输出分析结果，内容要有深度和实用性。"""


# 想法/文字提炼 prompt
IDEA_EXTRACTION_PROMPT = """你是一位善于提炼知识的专家。请分析以下内容，帮我提炼和整理成结构化的知识。

## 原始内容
{content}

---

请帮我：

## 一、内容整理
1. **核心要点**：这段内容的核心是什么？（用 1-2 句话概括）
2. **关键信息**：有哪些重要的细节或信息？

## 二、知识提炼
判断这段内容属于哪种类型的知识，并进行相应的提炼：

如果是**思维模式**（关于如何思考问题）：
- 思考框架是什么？
- 适用于什么场景？
- 有什么注意事项？

如果是**行为原则**（关于什么时候做什么）：
- 场景：什么情况下适用？
- 原则：具体怎么做？
- 原因：为什么这样做？

如果是**方法论**（关于如何系统性解决问题）：
- 步骤：具体分几步？
- 关键点：每一步的要点是什么？
- 陷阱：要避免什么？

如果是**洞察**（深刻的认识或发现）：
- 洞察是什么？
- 为什么重要？
- 如何应用？

如果是**技术知识**（代码、架构、最佳实践等）：
- 技术要点是什么？
- 适用场景是什么？
- 有什么限制或注意事项？

## 三、建议的知识类型
根据内容，建议存储为哪种知识类型：
- thinking_pattern（思维模式）
- behavior_principle（行为原则）
- methodology（方法论）
- insight（洞察）
- best_practice（最佳实践）
- code_pattern（代码模式）

请给出你的判断和理由。

## 四、建议的标题
给这条知识起一个清晰、有意义的标题。

---
请直接输出分析结果。"""


class ContentLearner:
    """内容学习器 - 从各种内容中学习知识"""

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        llm_provider: Optional["LLMProvider"] = None,
        use_playwright: bool = True,
        max_pages: int = 5
    ):
        self.kb = knowledge_base
        self.llm = llm_provider
        self.scraper = WebScraper(use_playwright=use_playwright, max_pages=max_pages)

    async def learn_from_article(
        self,
        url: str,
        depth: int = 2,
        use_js: bool = True
    ) -> LearningResult:
        """从网页文章学习（支持多页爬取和 JS 渲染）

        Args:
            url: 文章 URL
            depth: 爬取深度（1=只抓首页，2=首页+子页面）
            use_js: 是否用 Playwright 渲染 JS

        Returns:
            学习结果
        """
        if not self.llm:
            return LearningResult(success=False, error="需要 LLM 来分析文章")

        # 使用智能爬虫抓取
        self.scraper.use_playwright = use_js
        scraped = await self.scraper.scrape(url, depth=depth)

        if scraped.error:
            return LearningResult(success=False, error=scraped.error)

        if not scraped.content or len(scraped.content.strip()) < 100:
            return LearningResult(
                success=False,
                error=f"内容太少（仅 {len(scraped.content)} 字符），可能是 SPA 页面或需要登录"
            )

        # 用 LLM 分析
        try:
            prompt = ARTICLE_ANALYSIS_PROMPT.format(content=scraped.content[:20000])
            messages = [{"role": "user", "content": prompt}]
            analysis = await self.llm.chat(messages)

            # 生成标题
            title = scraped.title or self._extract_title(url, analysis)

            # 存入知识库
            knowledge = self.kb.add(
                content=analysis,
                knowledge_type=KnowledgeType.INSIGHT,
                title=f"[文章学习] {title}",
                source=url,
                tags=["article", "学习笔记"],
                metadata={
                    "source_type": "article",
                    "url": url,
                    "pages_scraped": scraped.pages_scraped,
                    "content_length": len(scraped.content)
                }
            )

            return LearningResult(
                success=True,
                title=title,
                knowledge_type="insight",
                analysis=analysis,
                knowledge_id=knowledge.id,
                pages_scraped=scraped.pages_scraped,
                content_length=len(scraped.content)
            )

        except Exception as e:
            return LearningResult(success=False, error=str(e))

    async def learn_from_pdf(
        self,
        url_or_path: str
    ) -> LearningResult:
        """从 PDF 学习

        Args:
            url_or_path: PDF 的 URL 或本地路径

        Returns:
            学习结果
        """
        if not self.llm:
            return LearningResult(success=False, error="需要 LLM 来分析 PDF")

        # 抓取 PDF
        if url_or_path.startswith(('http://', 'https://')):
            scraped = await self.scraper._scrape_pdf(url_or_path)
        else:
            scraped = self.scraper.parse_pdf_file(url_or_path)

        if scraped.error:
            return LearningResult(success=False, error=scraped.error)

        if not scraped.content or len(scraped.content.strip()) < 100:
            return LearningResult(success=False, error="PDF 内容为空或太少")

        # 用 LLM 分析
        try:
            prompt = ARTICLE_ANALYSIS_PROMPT.format(content=scraped.content[:25000])
            messages = [{"role": "user", "content": prompt}]
            analysis = await self.llm.chat(messages)

            title = scraped.title or url_or_path.split('/')[-1]

            # 存入知识库
            knowledge = self.kb.add(
                content=analysis,
                knowledge_type=KnowledgeType.INSIGHT,
                title=f"[PDF学习] {title}",
                source=url_or_path,
                tags=["pdf", "学习笔记"],
                metadata={
                    "source_type": "pdf",
                    "url": url_or_path,
                    "content_length": len(scraped.content)
                }
            )

            return LearningResult(
                success=True,
                title=title,
                knowledge_type="insight",
                analysis=analysis,
                knowledge_id=knowledge.id,
                pages_scraped=1,
                content_length=len(scraped.content)
            )

        except Exception as e:
            return LearningResult(success=False, error=str(e))

    async def learn_from_idea(
        self,
        content: str,
        context: str = ""
    ) -> LearningResult:
        """从想法/文字学习

        Args:
            content: 想法或文字内容
            context: 上下文（可选）

        Returns:
            学习结果
        """
        if not self.llm:
            return LearningResult(success=False, error="需要 LLM 来提炼知识")

        if not content.strip():
            return LearningResult(success=False, error="内容不能为空")

        try:
            # 构建 prompt
            full_content = content
            if context:
                full_content = f"背景: {context}\n\n内容: {content}"

            prompt = IDEA_EXTRACTION_PROMPT.format(content=full_content)
            messages = [{"role": "user", "content": prompt}]
            analysis = await self.llm.chat(messages)

            # 解析建议的知识类型
            knowledge_type = self._parse_knowledge_type(analysis)

            # 解析标题
            title = self._parse_title(analysis, content)

            # 存入知识库
            knowledge = self.kb.add(
                content=analysis,
                knowledge_type=knowledge_type,
                title=title,
                source="user_input",
                tags=["idea", "提炼"],
                metadata={"source_type": "idea", "original": content[:500]}
            )

            return LearningResult(
                success=True,
                title=title,
                knowledge_type=knowledge_type.value,
                analysis=analysis,
                knowledge_id=knowledge.id
            )

        except Exception as e:
            return LearningResult(success=False, error=str(e))

    def _extract_title(self, url: str, analysis: str) -> str:
        """从分析结果中提取标题"""
        # 尝试从 URL 提取
        parts = url.rstrip('/').split('/')
        if parts:
            title = parts[-1].replace('-', ' ').replace('_', ' ')
            if len(title) > 5:
                return title[:50]

        # 从分析中提取第一个要点
        lines = analysis.split('\n')
        for line in lines:
            if '核心' in line or '观点' in line:
                # 找下一行作为标题
                idx = lines.index(line)
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1].strip()
                    if next_line and not next_line.startswith('#'):
                        return next_line[:50]

        return url.split('//')[-1].split('/')[0][:30]

    def _parse_knowledge_type(self, analysis: str) -> KnowledgeType:
        """从分析结果中解析知识类型"""
        analysis_lower = analysis.lower()

        type_keywords = {
            KnowledgeType.THINKING_PATTERN: ['thinking_pattern', '思维模式'],
            KnowledgeType.BEHAVIOR_PRINCIPLE: ['behavior_principle', '行为原则'],
            KnowledgeType.METHODOLOGY: ['methodology', '方法论'],
            KnowledgeType.INSIGHT: ['insight', '洞察'],
            KnowledgeType.BEST_PRACTICE: ['best_practice', '最佳实践'],
            KnowledgeType.CODE_PATTERN: ['code_pattern', '代码模式'],
        }

        for kt, keywords in type_keywords.items():
            for kw in keywords:
                if kw in analysis_lower:
                    return kt

        return KnowledgeType.INSIGHT

    def _parse_title(self, analysis: str, original: str) -> str:
        """从分析结果中解析标题"""
        # 查找"建议的标题"部分
        lines = analysis.split('\n')
        for i, line in enumerate(lines):
            if '建议的标题' in line or '标题' in line:
                # 查找下面非空行
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith('#') and not next_line.startswith('-'):
                        # 清理 markdown 格式
                        title = re.sub(r'[*_`]', '', next_line)
                        return title[:60]

        # 回退：使用原始内容前 30 字符
        return original[:30].replace('\n', ' ') + "..."
