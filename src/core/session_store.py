"""会话持久化存储 - 使用 SQLite"""
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from dataclasses import asdict

from .message import Message


class SessionStore:
    """SQLite 会话存储

    存储内容：
    - 会话元数据（session_id, created_at, last_activity）
    - 消息历史（MessageBus 中的所有消息）
    - Agent 状态（state, current_plan, conversation_history）
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "sessions.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            # 消息历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    from_agent TEXT NOT NULL,
                    to_agent TEXT NOT NULL,
                    msg_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id)
            """)

            # Agent 状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_states (
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    current_plan TEXT,
                    conversation_history TEXT DEFAULT '[]',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, agent_id),
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)

    # ========== 会话管理 ==========

    def create_session(self, session_id: Optional[str] = None) -> str:
        """创建新会话"""
        if session_id is None:
            session_id = str(uuid.uuid4())

        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (id, created_at, last_activity) VALUES (?, ?, ?)",
                (session_id, now, now)
            )
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """获取会话信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def update_session_activity(self, session_id: str):
        """更新会话最后活动时间"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET last_activity = ? WHERE id = ?",
                (now, session_id)
            )

    def get_latest_session(self) -> Optional[str]:
        """获取最近的会话 ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM sessions ORDER BY last_activity DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return row["id"]
        return None

    def delete_session(self, session_id: str):
        """删除会话及其所有数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM agent_states WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    # ========== 消息持久化 ==========

    def save_message(self, session_id: str, message: Message):
        """保存消息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO messages
                (id, session_id, content, from_agent, to_agent, msg_type, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                session_id,
                message.content,
                message.from_agent,
                message.to_agent,
                message.msg_type,
                message.timestamp.isoformat(),
                json.dumps(message.metadata)
            ))
        # 更新会话活动时间
        self.update_session_activity(session_id)

    def get_messages(self, session_id: str, limit: int = 100) -> list[Message]:
        """获取会话消息历史"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (session_id, limit))
            rows = cursor.fetchall()

            messages = []
            for row in rows:
                messages.append(Message(
                    id=row["id"],
                    content=row["content"],
                    from_agent=row["from_agent"],
                    to_agent=row["to_agent"],
                    msg_type=row["msg_type"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=json.loads(row["metadata"])
                ))
            return messages

    # ========== Agent 状态持久化 ==========

    def save_agent_state(
        self,
        session_id: str,
        agent_id: str,
        state: str,
        current_plan: Optional[dict] = None,
        conversation_history: Optional[list] = None
    ):
        """保存 Agent 状态"""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO agent_states
                (session_id, agent_id, state, current_plan, conversation_history, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                agent_id,
                state,
                json.dumps(current_plan) if current_plan else None,
                json.dumps(conversation_history or []),
                now
            ))

    def get_agent_state(self, session_id: str, agent_id: str) -> Optional[dict]:
        """获取 Agent 状态"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_states
                WHERE session_id = ? AND agent_id = ?
            """, (session_id, agent_id))
            row = cursor.fetchone()

            if row:
                return {
                    "agent_id": row["agent_id"],
                    "state": row["state"],
                    "current_plan": json.loads(row["current_plan"]) if row["current_plan"] else None,
                    "conversation_history": json.loads(row["conversation_history"]),
                    "updated_at": row["updated_at"]
                }
        return None

    def get_all_agent_states(self, session_id: str) -> dict[str, dict]:
        """获取会话中所有 Agent 的状态"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agent_states WHERE session_id = ?",
                (session_id,)
            )
            rows = cursor.fetchall()

            states = {}
            for row in rows:
                states[row["agent_id"]] = {
                    "state": row["state"],
                    "current_plan": json.loads(row["current_plan"]) if row["current_plan"] else None,
                    "conversation_history": json.loads(row["conversation_history"]),
                    "updated_at": row["updated_at"]
                }
            return states


# 全局单例
_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """获取会话存储单例"""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
