"""Memory System - 记忆与知识管理

组件：
- MemoryStore: 简单记忆存储（关键词搜索）
- KnowledgeBase: 知识库（向量搜索）
- GitHubLearner: GitHub 学习器
- KnowledgeCurator: 知识管家（审查和管理）

架构设计（可插拔）：
- EmbeddingProvider: 文本向量化（local / openai）
- VectorStore: 向量存储（chroma / faiss）
"""
from .store import MemoryStore, LocalMemoryStore, Memory
from .embedding import EmbeddingProvider, LocalEmbedding, OpenAIEmbedding, create_embedding_provider
from .vector_store import VectorStore, ChromaVectorStore, FAISSVectorStore, Document, SearchResult, create_vector_store
from .knowledge_base import KnowledgeBase, Knowledge, KnowledgeType, RetrievalResult, create_knowledge_base
from .github_learner import GitHubLearner, learn_from_github
from .knowledge_curator import KnowledgeCurator, ReviewResult, ReviewRecommendation

__all__ = [
    # 基础记忆
    "MemoryStore",
    "LocalMemoryStore",
    "Memory",

    # Embedding
    "EmbeddingProvider",
    "LocalEmbedding",
    "OpenAIEmbedding",
    "create_embedding_provider",

    # VectorStore
    "VectorStore",
    "ChromaVectorStore",
    "FAISSVectorStore",
    "Document",
    "SearchResult",
    "create_vector_store",

    # KnowledgeBase
    "KnowledgeBase",
    "Knowledge",
    "KnowledgeType",
    "RetrievalResult",
    "create_knowledge_base",

    # GitHub
    "GitHubLearner",
    "learn_from_github",

    # Curator
    "KnowledgeCurator",
    "ReviewResult",
    "ReviewRecommendation",
]
