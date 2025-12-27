"""Vector Store - 可插拔的向量数据库模块"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any
from pathlib import Path


@dataclass
class Document:
    """文档对象"""
    id: str
    content: str
    metadata: dict
    embedding: Optional[list[float]] = None


@dataclass
class SearchResult:
    """搜索结果"""
    document: Document
    score: float  # 相似度分数，越高越相似


class VectorStore(ABC):
    """向量数据库抽象接口 - 可随时替换实现"""

    @abstractmethod
    def add(self, doc_id: str, content: str, embedding: list[float], metadata: dict = None) -> None:
        """添加文档"""
        pass

    @abstractmethod
    def add_batch(self, documents: list[Document]) -> None:
        """批量添加"""
        pass

    @abstractmethod
    def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        """向量搜索"""
        pass

    @abstractmethod
    def delete(self, doc_id: str) -> bool:
        """删除文档"""
        pass

    @abstractmethod
    def get(self, doc_id: str) -> Optional[Document]:
        """获取单个文档"""
        pass

    @abstractmethod
    def count(self) -> int:
        """文档数量"""
        pass


class ChromaVectorStore(VectorStore):
    """ChromaDB 实现 - 本地向量数据库

    特点：
    - 纯 Python，无需额外服务
    - 支持持久化存储
    - 自带向量索引，搜索快
    """

    def __init__(self, collection_name: str = "knowledge", persist_dir: str = "data/chroma"):
        self.collection_name = collection_name
        self.persist_dir = Path(persist_dir)
        self._client = None
        self._collection = None

    def _init_db(self):
        """初始化数据库 - 延迟加载"""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings

                self.persist_dir.mkdir(parents=True, exist_ok=True)

                # 创建持久化客户端
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_dir),
                    settings=Settings(anonymized_telemetry=False)
                )

                # 获取或创建 collection
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
                )

                print(f"ChromaDB 初始化完成，文档数: {self._collection.count()}")

            except ImportError:
                raise ImportError("请安装 chromadb: pip install chromadb")

    def add(self, doc_id: str, content: str, embedding: list[float], metadata: dict = None) -> None:
        """添加文档"""
        self._init_db()
        self._collection.upsert(
            ids=[doc_id],
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata or {}]
        )

    def add_batch(self, documents: list[Document]) -> None:
        """批量添加"""
        if not documents:
            return

        self._init_db()
        self._collection.upsert(
            ids=[d.id for d in documents],
            documents=[d.content for d in documents],
            embeddings=[d.embedding for d in documents],
            metadatas=[d.metadata for d in documents]
        )

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        """向量搜索"""
        self._init_db()

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                doc = Document(
                    id=doc_id,
                    content=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {}
                )
                # ChromaDB 返回的是距离，转换为相似度
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance  # 余弦距离转相似度

                search_results.append(SearchResult(document=doc, score=score))

        return search_results

    def delete(self, doc_id: str) -> bool:
        """删除文档"""
        self._init_db()
        try:
            self._collection.delete(ids=[doc_id])
            return True
        except:
            return False

    def get(self, doc_id: str) -> Optional[Document]:
        """获取单个文档"""
        self._init_db()
        try:
            result = self._collection.get(
                ids=[doc_id],
                include=["documents", "metadatas", "embeddings"]
            )
            if result["ids"]:
                return Document(
                    id=result["ids"][0],
                    content=result["documents"][0] if result["documents"] else "",
                    metadata=result["metadatas"][0] if result["metadatas"] else {},
                    embedding=result["embeddings"][0] if result["embeddings"] else None
                )
        except:
            pass
        return None

    def count(self) -> int:
        """文档数量"""
        self._init_db()
        return self._collection.count()

    def list_all(self, limit: int = 100) -> list[Document]:
        """列出所有文档"""
        self._init_db()
        result = self._collection.get(
            limit=limit,
            include=["documents", "metadatas"]
        )
        documents = []
        for i, doc_id in enumerate(result["ids"]):
            documents.append(Document(
                id=doc_id,
                content=result["documents"][i] if result["documents"] else "",
                metadata=result["metadatas"][i] if result["metadatas"] else {}
            ))
        return documents


class FAISSVectorStore(VectorStore):
    """FAISS 实现 - 高性能向量搜索

    特点：
    - 搜索更快（Facebook开发）
    - 纯内存，需要手动持久化
    - 适合大规模数据
    """

    def __init__(self, dimension: int, index_path: str = "data/faiss"):
        self.dimension = dimension
        self.index_path = Path(index_path)
        self._index = None
        self._id_to_doc: dict[str, Document] = {}
        self._id_to_idx: dict[str, int] = {}
        self._idx_to_id: dict[int, str] = {}
        self._current_idx = 0

    def _init_index(self):
        """初始化索引"""
        if self._index is None:
            try:
                import faiss

                self.index_path.mkdir(parents=True, exist_ok=True)

                # 尝试加载现有索引
                index_file = self.index_path / "index.faiss"
                meta_file = self.index_path / "meta.json"

                if index_file.exists() and meta_file.exists():
                    self._index = faiss.read_index(str(index_file))
                    import json
                    with open(meta_file, "r") as f:
                        meta = json.load(f)
                        self._id_to_doc = {k: Document(**v) for k, v in meta["docs"].items()}
                        self._id_to_idx = meta["id_to_idx"]
                        self._idx_to_id = {int(k): v for k, v in meta["idx_to_id"].items()}
                        self._current_idx = meta["current_idx"]
                else:
                    # 创建新索引 - 使用 L2 距离
                    self._index = faiss.IndexFlatIP(self.dimension)  # 内积（用于归一化向量）

                print(f"FAISS 初始化完成，文档数: {self._index.ntotal}")

            except ImportError:
                raise ImportError("请安装 faiss-cpu: pip install faiss-cpu")

    def _save(self):
        """保存索引"""
        import faiss
        import json

        index_file = self.index_path / "index.faiss"
        meta_file = self.index_path / "meta.json"

        faiss.write_index(self._index, str(index_file))

        meta = {
            "docs": {k: {"id": v.id, "content": v.content, "metadata": v.metadata}
                     for k, v in self._id_to_doc.items()},
            "id_to_idx": self._id_to_idx,
            "idx_to_id": {str(k): v for k, v in self._idx_to_id.items()},
            "current_idx": self._current_idx
        }
        with open(meta_file, "w") as f:
            json.dump(meta, f)

    def add(self, doc_id: str, content: str, embedding: list[float], metadata: dict = None) -> None:
        """添加文档"""
        import numpy as np

        self._init_index()

        # 归一化向量
        vec = np.array([embedding], dtype=np.float32)
        faiss.normalize_L2(vec)

        self._index.add(vec)

        doc = Document(id=doc_id, content=content, metadata=metadata or {})
        self._id_to_doc[doc_id] = doc
        self._id_to_idx[doc_id] = self._current_idx
        self._idx_to_id[self._current_idx] = doc_id
        self._current_idx += 1

        self._save()

    def add_batch(self, documents: list[Document]) -> None:
        """批量添加"""
        import numpy as np
        import faiss

        if not documents:
            return

        self._init_index()

        # 准备向量
        vectors = np.array([d.embedding for d in documents], dtype=np.float32)
        faiss.normalize_L2(vectors)

        self._index.add(vectors)

        for doc in documents:
            self._id_to_doc[doc.id] = doc
            self._id_to_idx[doc.id] = self._current_idx
            self._idx_to_id[self._current_idx] = doc.id
            self._current_idx += 1

        self._save()

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        """向量搜索"""
        import numpy as np
        import faiss

        self._init_index()

        # 归一化查询向量
        query = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query)

        # 搜索
        scores, indices = self._index.search(query, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx in self._idx_to_id:
                doc_id = self._idx_to_id[idx]
                doc = self._id_to_doc.get(doc_id)
                if doc:
                    results.append(SearchResult(document=doc, score=float(score)))

        return results

    def delete(self, doc_id: str) -> bool:
        """删除文档 - FAISS 不支持删除，标记为已删除"""
        if doc_id in self._id_to_doc:
            del self._id_to_doc[doc_id]
            # 注意：FAISS 索引中的向量不会真正删除
            return True
        return False

    def get(self, doc_id: str) -> Optional[Document]:
        """获取单个文档"""
        return self._id_to_doc.get(doc_id)

    def count(self) -> int:
        """文档数量"""
        return len(self._id_to_doc)


def create_vector_store(
    store_type: str = "chroma",
    **kwargs
) -> VectorStore:
    """工厂函数 - 创建 VectorStore

    Args:
        store_type: "chroma" 或 "faiss"
        **kwargs: 其他参数

    Returns:
        VectorStore 实例
    """
    if store_type == "chroma":
        return ChromaVectorStore(**kwargs)
    elif store_type == "faiss":
        if "dimension" not in kwargs:
            raise ValueError("FAISS 需要指定 dimension 参数")
        return FAISSVectorStore(**kwargs)
    else:
        raise ValueError(f"未知的 VectorStore 类型: {store_type}")
