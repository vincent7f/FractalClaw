"""
Memory 组件 - 记忆组件

实现 OpenClaw 的持久化记忆功能
"""

# 标准库
import json
import sqlite3
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# 本地模块
from ..core.component import Component, ClientInterface, ServiceInterface
from ..exceptions import MemoryError
from ..logger import memory_logger


@dataclass
class MemoryItem:
    """记忆条目"""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
        }


class MemoryStore(ABC):
    """记忆存储抽象"""

    @abstractmethod
    def store(self, memory: MemoryItem) -> str:
        """存储记忆"""
        pass

    @abstractmethod
    def retrieve(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """检索记忆"""
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        pass

    @abstractmethod
    def update(self, memory: MemoryItem) -> bool:
        """更新记忆"""
        pass

    @abstractmethod
    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        pass

    @abstractmethod
    def list_all(self, limit: int = 100) -> List[MemoryItem]:
        """列出所有记忆"""
        pass


class InMemoryStore(MemoryStore):
    """内存存储"""

    def __init__(self):
        self._memories: Dict[str, MemoryItem] = {}

    def store(self, memory: MemoryItem) -> str:
        self._memories[memory.id] = memory
        return memory.id

    def retrieve(self, query: str, limit: int = 10) -> List[MemoryItem]:
        # 简单的关键词匹配
        results = []
        query_lower = query.lower()
        for memory in self._memories.values():
            if query_lower in memory.content.lower():
                results.append(memory)
                memory.accessed_at = datetime.now()
                memory.access_count += 1
        return results[:limit]

    def delete(self, memory_id: str) -> bool:
        return self._memories.pop(memory_id, None) is not None

    def update(self, memory: MemoryItem) -> bool:
        if memory.id in self._memories:
            self._memories[memory.id] = memory
            return True
        return False

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        return self._memories.get(memory_id)

    def list_all(self, limit: int = 100) -> List[MemoryItem]:
        return list(self._memories.values())[:limit]


class SQLiteMemoryStore(MemoryStore):
    """SQLite 持久化存储"""

    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding BLOB,
                        metadata TEXT,
                        created_at TEXT,
                        accessed_at TEXT,
                        access_count INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
                memory_logger.info(f"Database initialized: {self.db_path}")
        except sqlite3.Error as e:
            memory_logger.error(f"Failed to initialize database: {e}")
            raise MemoryError(
                message=f"Failed to initialize database: {str(e)}",
            ) from e

    def store(self, memory: MemoryItem) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO memories
                       (id, content, metadata, created_at, accessed_at, access_count)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        memory.id,
                        memory.content,
                        json.dumps(memory.metadata),
                        memory.created_at.isoformat(),
                        memory.accessed_at.isoformat(),
                        memory.access_count,
                    ),
                )
                conn.commit()
            return memory.id
        except sqlite3.Error as e:
            memory_logger.error(f"Failed to store memory: {e}")
            raise MemoryError(
                message=f"Failed to store memory: {str(e)}",
                memory_id=memory.id,
            ) from e

    def retrieve(self, query: str, limit: int = 10) -> List[MemoryItem]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT * FROM memories
                       WHERE content LIKE ? ORDER BY accessed_at DESC LIMIT ?""",
                    (f"%{query}%", limit),
                )
                rows = cursor.fetchall()

            results = []
            for row in rows:
                memory = MemoryItem(
                    id=row[0],
                    content=row[1],
                    metadata=json.loads(row[3]) if row[3] else {},
                    created_at=datetime.fromisoformat(row[4]),
                    accessed_at=datetime.fromisoformat(row[5]),
                    access_count=row[6],
                )
                results.append(memory)
            return results
        except sqlite3.Error as e:
            memory_logger.error(f"Failed to retrieve memories: {e}")
            raise MemoryError(
                message=f"Failed to retrieve memories: {str(e)}",
            ) from e

    def delete(self, memory_id: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                conn.commit()
                deleted = cursor.rowcount > 0
            return deleted
        except sqlite3.Error as e:
            memory_logger.error(f"Failed to delete memory: {e}")
            raise MemoryError(
                message=f"Failed to delete memory: {str(e)}",
                memory_id=memory_id,
            ) from e

    def update(self, memory: MemoryItem) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE memories
                       SET content=?, metadata=?, accessed_at=?, access_count=?
                       WHERE id=?""",
                    (
                        memory.content,
                        json.dumps(memory.metadata),
                        memory.accessed_at.isoformat(),
                        memory.access_count,
                        memory.id,
                    ),
                )
                conn.commit()
                updated = cursor.rowcount > 0
            return updated
        except sqlite3.Error as e:
            memory_logger.error(f"Failed to update memory: {e}")
            raise MemoryError(
                message=f"Failed to update memory: {str(e)}",
                memory_id=memory.id,
            ) from e

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
                row = cursor.fetchone()

            if row:
                return MemoryItem(
                    id=row[0],
                    content=row[1],
                    metadata=json.loads(row[3]) if row[3] else {},
                    created_at=datetime.fromisoformat(row[4]),
                    accessed_at=datetime.fromisoformat(row[5]),
                    access_count=row[6],
                )
            return None
        except sqlite3.Error as e:
            memory_logger.error(f"Failed to get memory: {e}")
            raise MemoryError(
                message=f"Failed to get memory: {str(e)}",
                memory_id=memory_id,
            ) from e

    def list_all(self, limit: int = 100) -> List[MemoryItem]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM memories ORDER BY accessed_at DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(
                    MemoryItem(
                        id=row[0],
                        content=row[1],
                        metadata=json.loads(row[3]) if row[3] else {},
                        created_at=datetime.fromisoformat(row[4]),
                        accessed_at=datetime.fromisoformat(row[5]),
                        access_count=row[6],
                    )
                )
            return results
        except sqlite3.Error as e:
            memory_logger.error(f"Failed to list memories: {e}")
            raise MemoryError(
                message=f"Failed to list memories: {str(e)}",
            ) from e


class MemoryComponent(Component):
    """
    记忆组件 - 提供持久化记忆功能

    支持:
    - 短期记忆 (工作记忆)
    - 长期记忆 (持久化存储)
    - 上下文管理
    """

    def __init__(self, name: str, store: Optional[MemoryStore] = None):
        super().__init__(name)
        self._store = store or InMemoryStore()
        self._working_memory: Dict[str, Any] = {}

        # 定义接口
        self.add_interface(
            ServiceInterface(
                "memory_interface",
                ["store", "retrieve", "get", "delete", "list", "clear"],
            )
        )
        self.add_interface(ClientInterface("client_interface", []))

    def store(self, key: str, value: Any, metadata: Optional[Dict] = None) -> str:
        """存储记忆"""
        memory = MemoryItem(
            id=str(uuid.uuid4()),
            content=str(value),
            metadata=metadata or {},
        )

        # 同时存储到工作记忆
        self._working_memory[key] = memory

        # 持久化存储
        return self._store.store(memory)

    def retrieve(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """检索记忆"""
        return self._store.retrieve(query, limit)

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        return self._store.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        return self._store.delete(memory_id)

    def list(self, limit: int = 100) -> List[MemoryItem]:
        """列出所有记忆"""
        return self._store.list_all(limit)

    def clear(self) -> None:
        """清空工作记忆"""
        self._working_memory.clear()

    def get_working_memory(self, key: str, default: Any = None) -> Any:
        """获取工作记忆"""
        return self._working_memory.get(key, default)

    def set_working_memory(self, key: str, value: Any) -> None:
        """设置工作记忆"""
        self._working_memory[key] = value

    def _on_initialize(self) -> None:
        pass

    def _on_start(self) -> None:
        pass

    def _on_stop(self) -> None:
        pass
