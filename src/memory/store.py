"""记忆系统 - 跨项目经验积累"""
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Memory:
    """记忆条目"""
    id: str
    content: str
    tags: list[str]
    source: str  # 来源agent
    project: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        return cls(**data)


class MemoryStore(ABC):
    """记忆存储接口"""

    @abstractmethod
    async def write(self, content: str, tags: list[str], source: str, project: Optional[str] = None, metadata: dict = None) -> Memory:
        """写入记忆"""
        pass

    @abstractmethod
    async def query(self, query: str, limit: int = 5) -> list[Memory]:
        """查询记忆（简单文本匹配，后续可升级为向量搜索）"""
        pass

    @abstractmethod
    async def get_by_tags(self, tags: list[str], limit: int = 10) -> list[Memory]:
        """按标签获取"""
        pass

    @abstractmethod
    async def get_by_project(self, project: str) -> list[Memory]:
        """获取项目相关记忆"""
        pass


class LocalMemoryStore(MemoryStore):
    """本地文件存储实现

    v0.1简单实现，后续可升级为向量数据库
    """

    def __init__(self, base_path: str = "data/memory"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.memories_file = self.base_path / "memories.json"
        self.memories: list[Memory] = self._load()
        self.counter = len(self.memories)

    def _load(self) -> list[Memory]:
        """加载记忆"""
        if self.memories_file.exists():
            try:
                with open(self.memories_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [Memory.from_dict(m) for m in data]
            except:
                pass
        return []

    def _save(self):
        """保存记忆"""
        with open(self.memories_file, "w", encoding="utf-8") as f:
            json.dump([m.to_dict() for m in self.memories], f, ensure_ascii=False, indent=2)

    async def write(self, content: str, tags: list[str], source: str, project: Optional[str] = None, metadata: dict = None) -> Memory:
        """写入记忆"""
        self.counter += 1
        memory = Memory(
            id=f"mem_{self.counter}",
            content=content,
            tags=tags,
            source=source,
            project=project,
            metadata=metadata or {}
        )
        self.memories.append(memory)
        self._save()
        return memory

    async def query(self, query: str, limit: int = 5) -> list[Memory]:
        """简单文本匹配查询"""
        query_lower = query.lower()
        results = []

        for memory in self.memories:
            score = 0
            # 内容匹配
            if query_lower in memory.content.lower():
                score += 2
            # 标签匹配
            for tag in memory.tags:
                if query_lower in tag.lower():
                    score += 1

            if score > 0:
                results.append((score, memory))

        # 按分数排序
        results.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in results[:limit]]

    async def get_by_tags(self, tags: list[str], limit: int = 10) -> list[Memory]:
        """按标签获取"""
        results = []
        tags_lower = [t.lower() for t in tags]

        for memory in self.memories:
            memory_tags_lower = [t.lower() for t in memory.tags]
            if any(t in memory_tags_lower for t in tags_lower):
                results.append(memory)

        return results[:limit]

    async def get_by_project(self, project: str) -> list[Memory]:
        """获取项目相关记忆"""
        return [m for m in self.memories if m.project == project]

    async def get_all(self, limit: int = 50) -> list[Memory]:
        """获取所有记忆"""
        return self.memories[-limit:]

    async def get_user_preferences(self) -> list[Memory]:
        """获取用户偏好"""
        return await self.get_by_tags(["偏好", "preference", "用户"])

    async def get_project_experiences(self) -> list[Memory]:
        """获取项目经验"""
        return await self.get_by_tags(["经验", "experience", "项目"])
