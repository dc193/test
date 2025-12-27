"""Embedding Provider - 可插拔的文本向量化模块"""
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class EmbeddingProvider(ABC):
    """Embedding 抽象接口 - 可随时替换实现"""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """将文本转换为向量"""
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量转换"""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """向量维度"""
        pass


class LocalEmbedding(EmbeddingProvider):
    """本地 Embedding 实现 - 使用 sentence-transformers

    默认使用 all-MiniLM-L6-v2，M1 Mac 友好（~80MB，快速）
    可换成 bge-small-zh-v1.5 获得更好的中文支持
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = None

    def _load_model(self):
        """延迟加载模型 - 只在第一次使用时加载"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"正在加载 Embedding 模型: {self.model_name}...")
                self._model = SentenceTransformer(self.model_name)
                # 获取维度
                test_embedding = self._model.encode("test")
                self._dimension = len(test_embedding)
                print(f"Embedding 模型加载完成，维度: {self._dimension}")
            except ImportError:
                raise ImportError(
                    "请安装 sentence-transformers: pip install sentence-transformers"
                )

    def embed(self, text: str) -> list[float]:
        """将文本转换为向量"""
        self._load_model()
        embedding = self._model.encode(text)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量转换 - 比单个调用更高效"""
        self._load_model()
        embeddings = self._model.encode(texts)
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        """向量维度"""
        self._load_model()
        return self._dimension


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI Embedding 实现 - 付费但质量更好

    使用 text-embedding-3-small，价格便宜质量好
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        import os
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._client = None
        # 已知维度
        self._dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def embed(self, text: str) -> list[float]:
        """将文本转换为向量"""
        client = self._get_client()
        response = client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量转换"""
        client = self._get_client()
        response = client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        """向量维度"""
        return self._dimensions.get(self.model, 1536)


def create_embedding_provider(
    provider_type: str = "local",
    model_name: Optional[str] = None,
    **kwargs
) -> EmbeddingProvider:
    """工厂函数 - 创建 Embedding Provider

    Args:
        provider_type: "local" 或 "openai"
        model_name: 模型名称
        **kwargs: 其他参数

    Returns:
        EmbeddingProvider 实例
    """
    if provider_type == "local":
        model = model_name or "all-MiniLM-L6-v2"
        return LocalEmbedding(model_name=model)
    elif provider_type == "openai":
        model = model_name or "text-embedding-3-small"
        return OpenAIEmbedding(model=model, **kwargs)
    else:
        raise ValueError(f"未知的 Embedding Provider: {provider_type}")
