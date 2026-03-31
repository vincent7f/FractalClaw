"""
实时画布 (Live Canvas)

可视化工作空间，支持实时协作
"""

from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import uuid
import json

from fractalclaw.core.component import Component, CompositeComponent, ComponentState


class ElementType(Enum):
    """元素类型"""
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    TEXT = "text"
    IMAGE = "image"
    LINE = "line"
    PATH = "path"
    NOTE = "note"
    STICKER = "sticker"


@dataclass
class CanvasElement:
    """画布元素"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: ElementType = ElementType.RECTANGLE
    x: float = 0
    y: float = 0
    width: float = 100
    height: float = 100
    rotation: float = 0
    content: str = ""
    style: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "content": self.content,
            "style": self.style,
            "metadata": self.metadata,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Canvas:
    """画布"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    width: float = 2000
    height: float = 1500
    background: str = "#ffffff"
    elements: Dict[str, CanvasElement] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "background": self.background,
            "elements": {k: v.to_dict() for k, v in self.elements.items()},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class CanvasUser:
    """画布用户"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    color: str = "#3B82F6"
    cursor_x: float = 0
    cursor_y: float = 0
    selected_elements: List[str] = field(default_factory=list)


# 事件处理器类型
CanvasEventHandler = Callable[[Dict[str, Any]], Awaitable[None]]


class LiveCanvas(CompositeComponent):
    """
    实时画布
    
    提供可视化工作空间，支持:
    - 多元素绘制
    - 实时协作
    - 元素操作（移动、缩放、旋转）
    - 历史记录
    """

    def __init__(self, name: str = "canvas"):
        super().__init__(name)
        
        self._canvases: Dict[str, Canvas] = {}
        self._users: Dict[str, CanvasUser] = {}
        self._handlers: Dict[str, CanvasEventHandler] = {}
        self._history: Dict[str, List[Dict]] = {}  # canvas_id -> history
        self._max_history = 50

    # ==================== 画布管理 ====================

    def create_canvas(
        self,
        name: str,
        width: float = 2000,
        height: float = 1500,
        background: str = "#ffffff",
    ) -> Canvas:
        """创建画布"""
        canvas = Canvas(
            name=name,
            width=width,
            height=height,
            background=background,
        )
        
        self._canvases[canvas.id] = canvas
        self._history[canvas.id] = []
        
        return canvas

    def get_canvas(self, canvas_id: str) -> Optional[Canvas]:
        """获取画布"""
        return self._canvases.get(canvas_id)

    def delete_canvas(self, canvas_id: str) -> bool:
        """删除画布"""
        return self._canvases.pop(canvas_id, None) is not None

    def list_canvases(self) -> List[Canvas]:
        """列出所有画布"""
        return list(self._canvases.values())

    # ==================== 元素操作 ====================

    def add_element(
        self,
        canvas_id: str,
        element: CanvasElement,
    ) -> Optional[CanvasElement]:
        """添加元素"""
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            return None
        
        canvas.elements[element.id] = element
        canvas.updated_at = datetime.now()
        
        # 记录历史
        self._record_history(canvas_id, "add", element.to_dict())
        
        return element

    def update_element(
        self,
        canvas_id: str,
        element_id: str,
        updates: Dict[str, Any],
    ) -> Optional[CanvasElement]:
        """更新元素"""
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            return None
        
        element = canvas.elements.get(element_id)
        if not element:
            return None
        
        # 记录旧状态
        old_state = element.to_dict()
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(element, key):
                setattr(element, key, value)
        
        element.updated_at = datetime.now()
        canvas.updated_at = datetime.now()
        
        # 记录历史
        self._record_history(canvas_id, "update", {
            "old": old_state,
            "new": element.to_dict(),
        })
        
        return element

    def delete_element(
        self,
        canvas_id: str,
        element_id: str,
    ) -> bool:
        """删除元素"""
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            return False
        
        element = canvas.elements.pop(element_id, None)
        if element:
            canvas.updated_at = datetime.now()
            self._record_history(canvas_id, "delete", element.to_dict())
            return True
        
        return False

    def get_element(
        self,
        canvas_id: str,
        element_id: str,
    ) -> Optional[CanvasElement]:
        """获取元素"""
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            return None
        
        return canvas.elements.get(element_id)

    # ==================== 用户管理 ====================

    def add_user(
        self,
        user_id: str,
        name: str,
        color: str = "#3B82F6",
    ) -> CanvasUser:
        """添加用户"""
        user = CanvasUser(
            id=user_id,
            name=name,
            color=color,
        )
        
        self._users[user_id] = user
        return user

    def remove_user(self, user_id: str) -> bool:
        """移除用户"""
        return self._users.pop(user_id, None) is not None

    def update_user_cursor(
        self,
        user_id: str,
        x: float,
        y: float,
    ) -> Optional[CanvasUser]:
        """更新用户光标"""
        user = self._users.get(user_id)
        if user:
            user.cursor_x = x
            user.cursor_y = y
        return user

    def select_elements(
        self,
        user_id: str,
        element_ids: List[str],
    ) -> Optional[CanvasUser]:
        """选择元素"""
        user = self._users.get(user_id)
        if user:
            user.selected_elements = element_ids
        return user

    def list_users(self) -> List[CanvasUser]:
        """列出所有用户"""
        return list(self._users.values())

    # ==================== 历史记录 ====================

    def _record_history(
        self,
        canvas_id: str,
        action: str,
        data: Dict[str, Any],
    ):
        """记录历史"""
        if canvas_id not in self._history:
            self._history[canvas_id] = []
        
        self._history[canvas_id].append({
            "action": action,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })
        
        # 限制历史长度
        if len(self._history[canvas_id]) > self._max_history:
            self._history[canvas_id] = self._history[canvas_id][-self._max_history:]

    def get_history(
        self,
        canvas_id: str,
        limit: int = 20,
    ) -> List[Dict]:
        """获取历史"""
        history = self._history.get(canvas_id, [])
        return history[-limit:]

    def undo(self, canvas_id: str) -> bool:
        """撤销"""
        history = self._history.get(canvas_id, [])
        if not history:
            return False
        
        last_action = history.pop()
        
        # 反向操作
        if last_action["action"] == "add":
            # 删除添加的元素
            element_id = last_action["data"]["id"]
            self._canvases[canvas_id].elements.pop(element_id, None)
        
        elif last_action["action"] == "delete":
            # 恢复删除的元素
            pass  # 需要保存完整状态
        
        elif last_action["action"] == "update":
            # 恢复旧状态
            old = last_action["data"]["old"]
            element_id = old["id"]
            if element_id in self._canvases[canvas_id].elements:
                for key, value in old.items():
                    setattr(self._canvases[canvas_id].elements[element_id], key, value)
        
        return True

    # ==================== 事件处理 ====================

    def register_handler(self, event: str, handler: CanvasEventHandler):
        """注册事件处理器"""
        self._handlers[event] = handler

    async def emit_event(self, event: str, data: Dict[str, Any]):
        """触发事件"""
        handler = self._handlers.get(event)
        if handler:
            await handler(data)

    # ==================== WebSocket 集成 ====================

    async def broadcast_canvas_update(
        self,
        canvas_id: str,
        update_type: str,
        data: Dict[str, Any],
    ):
        """广播画布更新"""
        await self.emit_event("canvas_update", {
            "canvas_id": canvas_id,
            "type": update_type,
            "data": data,
        })

    async def broadcast_cursor_update(
        self,
        user_id: str,
        canvas_id: str,
        x: float,
        y: float,
    ):
        """广播光标更新"""
        await self.emit_event("cursor_update", {
            "user_id": user_id,
            "canvas_id": canvas_id,
            "x": x,
            "y": y,
        })

    # ==================== 工具方法 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        total_elements = sum(len(c.elements) for c in self._canvases.values())
        return {
            "canvases_count": len(self._canvases),
            "total_elements": total_elements,
            "users_count": len(self._users),
        }

    def export_canvas(self, canvas_id: str) -> Optional[str]:
        """导出画布为 JSON"""
        canvas = self._canvases.get(canvas_id)
        if canvas:
            return json.dumps(canvas.to_dict(), indent=2)
        return None

    def import_canvas(self, json_str: str) -> Optional[Canvas]:
        """从 JSON 导入画布"""
        try:
            data = json.loads(json_str)
            canvas = Canvas(
                id=data.get("id", str(uuid.uuid4())),
                name=data.get("name", ""),
                width=data.get("width", 2000),
                height=data.get("height", 1500),
                background=data.get("background", "#ffffff"),
            )
            
            for elem_data in data.get("elements", {}).values():
                element = CanvasElement(
                    id=elem_data.get("id", str(uuid.uuid4())),
                    type=ElementType(elem_data.get("type", "rectangle")),
                    x=elem_data.get("x", 0),
                    y=elem_data.get("y", 0),
                    width=elem_data.get("width", 100),
                    height=elem_data.get("height", 100),
                    content=elem_data.get("content", ""),
                    style=elem_data.get("style", {}),
                )
                canvas.elements[element.id] = element
            
            self._canvases[canvas.id] = canvas
            self._history[canvas.id] = []
            
            return canvas
            
        except Exception:
            return None
