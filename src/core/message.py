"""消息定义"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Message:
    """Agent之间的消息"""
    content: str
    from_agent: str
    to_agent: str = "all"
    msg_type: str = "chat"  # chat, task, report, alert, question
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "msg_type": self.msg_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
