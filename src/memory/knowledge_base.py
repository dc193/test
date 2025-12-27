"""Knowledge Base - 知识库模块

整合 Embedding + VectorStore，提供完整的知识管理能力
支持：
- 项目经验存储
- GitHub 仓库学习
- 智能检索
"""
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum

from .embedding import EmbeddingProvider, create_embedding_provider
from .vector_store import VectorStore, Document, SearchResult, create_vector_store


class KnowledgeType(str, Enum):
    """知识类型"""
    # 技术知识
    PROJECT_EXPERIENCE = "project_experience"  # 项目经验
    CODE_PATTERN = "code_pattern"              # 代码模式
    BEST_PRACTICE = "best_practice"            # 最佳实践
    GITHUB_EXAMPLE = "github_example"          # GitHub 示例
    DOCUMENTATION = "documentation"            # 文档

    # 思想与方法论
    THINKING_PATTERN = "thinking_pattern"      # 思维模式（为什么这样做）
    BEHAVIOR_PRINCIPLE = "behavior_principle"  # 行为原则（什么时候做什么）
    METHODOLOGY = "methodology"                # 方法论（怎么系统性解决问题）
    INSIGHT = "insight"                        # 洞察（深刻的认识）

    # 反馈
    USER_FEEDBACK = "user_feedback"            # 用户反馈


@dataclass
class Knowledge:
    """知识条目

    包含知识的内容、类型、来源，以及人格化属性（专家角色）
    """
    id: str
    content: str
    knowledge_type: KnowledgeType
    title: str = ""
    source: str = ""  # 来源（如 GitHub URL, 项目名）
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)

    # 人格化属性 - 知识属于哪些"专家"
    personas: list[str] = field(default_factory=list)  # 专家角色列表
    perspective: str = ""  # 这条知识的视角/切入点

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "knowledge_type": self.knowledge_type.value,
            "title": self.title,
            "source": self.source,
            "tags": self.tags,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "personas": self.personas,
            "perspective": self.perspective
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Knowledge":
        data["knowledge_type"] = KnowledgeType(data["knowledge_type"])
        # 兼容旧数据
        if "personas" not in data:
            data["personas"] = []
        if "perspective" not in data:
            data["perspective"] = ""
        return cls(**data)


@dataclass
class RetrievalResult:
    """检索结果"""
    knowledge: Knowledge
    relevance_score: float


class KnowledgeBase:
    """知识库 - God Layer 的长期记忆

    特点：
    - 可插拔的 Embedding 和 VectorStore
    - 支持多种知识类型
    - 智能检索
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None,
        data_dir: str = "data/knowledge"
    ):
        """初始化知识库

        Args:
            embedding_provider: Embedding 提供者，默认使用本地模型
            vector_store: 向量存储，默认使用 ChromaDB
            data_dir: 数据目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 延迟初始化
        self._embedding = embedding_provider
        self._vector_store = vector_store
        self._initialized = False

        # 元数据文件
        self.meta_file = self.data_dir / "knowledge_meta.json"
        self._knowledge_meta: dict[str, Knowledge] = {}

        self._load_meta()

    def _ensure_initialized(self):
        """确保组件已初始化"""
        if not self._initialized:
            if self._embedding is None:
                self._embedding = create_embedding_provider("local")
            if self._vector_store is None:
                self._vector_store = create_vector_store(
                    "chroma",
                    collection_name="knowledge",
                    persist_dir=str(self.data_dir / "chroma")
                )
            self._initialized = True

    def _load_meta(self):
        """加载元数据"""
        if self.meta_file.exists():
            try:
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._knowledge_meta = {
                        k: Knowledge.from_dict(v) for k, v in data.items()
                    }
            except Exception as e:
                print(f"加载知识库元数据失败: {e}")

    def _save_meta(self):
        """保存元数据"""
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.to_dict() for k, v in self._knowledge_meta.items()},
                f,
                ensure_ascii=False,
                indent=2
            )

    def _generate_id(self, content: str) -> str:
        """生成唯一 ID"""
        hash_val = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"kb_{hash_val}"

    def add(
        self,
        content: str,
        knowledge_type: KnowledgeType,
        title: str = "",
        source: str = "",
        tags: list[str] = None,
        metadata: dict = None,
        personas: list[str] = None,
        perspective: str = ""
    ) -> Knowledge:
        """添加知识

        Args:
            content: 知识内容
            knowledge_type: 知识类型
            title: 标题
            source: 来源
            tags: 标签
            metadata: 额外元数据
            personas: 专家角色列表
            perspective: 知识视角

        Returns:
            Knowledge 对象
        """
        self._ensure_initialized()

        # 创建知识对象
        knowledge_id = self._generate_id(content)
        knowledge = Knowledge(
            id=knowledge_id,
            content=content,
            knowledge_type=knowledge_type,
            title=title,
            source=source,
            tags=tags or [],
            metadata=metadata or {},
            personas=personas or [],
            perspective=perspective
        )

        # 生成 embedding
        embedding = self._embedding.embed(content)

        # 存入向量数据库
        self._vector_store.add(
            doc_id=knowledge_id,
            content=content,
            embedding=embedding,
            metadata={
                "type": knowledge_type.value,
                "title": title,
                "source": source,
                "tags": ",".join(tags or [])
            }
        )

        # 保存元数据
        self._knowledge_meta[knowledge_id] = knowledge
        self._save_meta()

        print(f"知识已添加: [{knowledge_type.value}] {title or content[:50]}...")
        return knowledge

    def add_batch(self, knowledge_list: list[Knowledge]) -> int:
        """批量添加知识

        Returns:
            添加数量
        """
        self._ensure_initialized()

        if not knowledge_list:
            return 0

        # 批量生成 embedding
        contents = [k.content for k in knowledge_list]
        embeddings = self._embedding.embed_batch(contents)

        # 准备文档
        documents = []
        for knowledge, embedding in zip(knowledge_list, embeddings):
            if not knowledge.id:
                knowledge.id = self._generate_id(knowledge.content)

            doc = Document(
                id=knowledge.id,
                content=knowledge.content,
                embedding=embedding,
                metadata={
                    "type": knowledge.knowledge_type.value,
                    "title": knowledge.title,
                    "source": knowledge.source,
                    "tags": ",".join(knowledge.tags)
                }
            )
            documents.append(doc)
            self._knowledge_meta[knowledge.id] = knowledge

        # 批量存入
        self._vector_store.add_batch(documents)
        self._save_meta()

        print(f"批量添加 {len(documents)} 条知识")
        return len(documents)

    def search(
        self,
        query: str,
        top_k: int = 5,
        knowledge_type: Optional[KnowledgeType] = None,
        min_score: float = 0.3
    ) -> list[RetrievalResult]:
        """智能检索

        Args:
            query: 查询文本
            top_k: 返回数量
            knowledge_type: 过滤类型
            min_score: 最低相似度

        Returns:
            检索结果列表
        """
        self._ensure_initialized()

        # 生成查询向量
        query_embedding = self._embedding.embed(query)

        # 向量搜索（多取一些用于过滤）
        search_results = self._vector_store.search(query_embedding, top_k=top_k * 2)

        # 过滤和转换
        results = []
        for sr in search_results:
            if sr.score < min_score:
                continue

            # 类型过滤
            if knowledge_type:
                doc_type = sr.document.metadata.get("type")
                if doc_type != knowledge_type.value:
                    continue

            # 获取完整知识对象
            knowledge = self._knowledge_meta.get(sr.document.id)
            if knowledge:
                results.append(RetrievalResult(
                    knowledge=knowledge,
                    relevance_score=sr.score
                ))

            if len(results) >= top_k:
                break

        return results

    def get_by_type(self, knowledge_type: KnowledgeType, limit: int = 20) -> list[Knowledge]:
        """按类型获取"""
        return [
            k for k in self._knowledge_meta.values()
            if k.knowledge_type == knowledge_type
        ][:limit]

    def get_by_source(self, source: str) -> list[Knowledge]:
        """按来源获取"""
        return [
            k for k in self._knowledge_meta.values()
            if source.lower() in k.source.lower()
        ]

    def get_by_tags(self, tags: list[str]) -> list[Knowledge]:
        """按标签获取"""
        tags_lower = [t.lower() for t in tags]
        results = []
        for k in self._knowledge_meta.values():
            k_tags_lower = [t.lower() for t in k.tags]
            if any(t in k_tags_lower for t in tags_lower):
                results.append(k)
        return results

    def get_by_personas(self, personas: list[str]) -> list[Knowledge]:
        """按专家角色获取"""
        personas_lower = [p.lower() for p in personas]
        results = []
        for k in self._knowledge_meta.values():
            k_personas_lower = [p.lower() for p in k.personas]
            if any(p in k_personas_lower for p in personas_lower):
                results.append(k)
        return results

    def search_with_personas(
        self,
        query: str,
        personas: list[str] = None,
        top_k: int = 5,
        min_score: float = 0.3
    ) -> list[RetrievalResult]:
        """带专家角色过滤的智能检索

        优先返回匹配指定专家角色的知识
        """
        self._ensure_initialized()

        # 先做向量搜索
        query_embedding = self._embedding.embed(query)
        search_results = self._vector_store.search(query_embedding, top_k=top_k * 3)

        results = []
        persona_matched = []
        other_matched = []

        for sr in search_results:
            if sr.score < min_score:
                continue

            knowledge = self._knowledge_meta.get(sr.document.id)
            if not knowledge:
                continue

            result = RetrievalResult(knowledge=knowledge, relevance_score=sr.score)

            # 如果指定了 personas，优先匹配
            if personas:
                k_personas_lower = [p.lower() for p in knowledge.personas]
                if any(p.lower() in k_personas_lower for p in personas):
                    persona_matched.append(result)
                else:
                    other_matched.append(result)
            else:
                other_matched.append(result)

        # 组合结果：专家匹配的优先
        results = persona_matched + other_matched
        return results[:top_k]

    def delete(self, knowledge_id: str) -> bool:
        """删除知识"""
        self._ensure_initialized()

        if knowledge_id in self._knowledge_meta:
            del self._knowledge_meta[knowledge_id]
            self._vector_store.delete(knowledge_id)
            self._save_meta()
            return True
        return False

    def count(self) -> int:
        """知识数量"""
        return len(self._knowledge_meta)

    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {
            "total": self.count(),
            "by_type": {}
        }
        for k in self._knowledge_meta.values():
            t = k.knowledge_type.value
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
        return stats


# 便捷函数
def create_knowledge_base(
    embedding_type: str = "local",
    store_type: str = "chroma",
    data_dir: str = "data/knowledge",
    **kwargs
) -> KnowledgeBase:
    """创建知识库

    Args:
        embedding_type: "local" 或 "openai"
        store_type: "chroma" 或 "faiss"
        data_dir: 数据目录
        **kwargs: 其他参数

    Returns:
        KnowledgeBase 实例
    """
    embedding = create_embedding_provider(embedding_type)

    # ChromaDB 不需要 dimension，只有 FAISS 需要
    if store_type == "faiss":
        vector_store = create_vector_store(
            store_type,
            persist_dir=str(Path(data_dir) / store_type),
            dimension=embedding.dimension
        )
    else:
        vector_store = create_vector_store(
            store_type,
            persist_dir=str(Path(data_dir) / store_type)
        )

    return KnowledgeBase(
        embedding_provider=embedding,
        vector_store=vector_store,
        data_dir=data_dir
    )
