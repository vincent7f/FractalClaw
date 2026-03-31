"""
MessageRouter 组件 - 消息路由组件

实现 OpenClaw 的多平台消息路由功能
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

from ..core.component import Component, ClientInterface, ServiceInterface


class Platform(Enum):
    """消息平台"""
    TERMINAL = "terminal"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


@dataclass
class Message:
    """消息"""
    id: str
    platform: Platform
    content: str
    sender: str
    receiver: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform.value,
            "content": self.content,
            "sender": self.sender,
            "receiver": self.receiver,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MessageHandler:
    """消息处理器"""
    platform: Platform
    handler: Callable
    enabled: bool = True
    
    async def process(self, message: Message) -> Any:
        """处理消息"""
        if asyncio.iscoroutinefunction(self.handler):
            return await self.handler(message)
        return self.handler(message)


class MessageRouterComponent(Component):
    """
    消息路由组件 - 多平台消息统一管理
    
    支持:
    - 多平台消息接收
    - 消息转发
    - 消息过滤
    - 统一 API
    """
    
    def __init__(self, name: str):
        super().__init__(name)
        self._handlers: Dict[Platform, List[MessageHandler]] = {}
        self._message_history: List[Message] = []
        self._max_history = 1000
        self._routing_rules: List[Callable] = []
        
        # 定义接口
        self.add_interface(ServiceInterface("message_router_interface", [
            "send_message", "register_handler", "route_message"
        ]))
        self.add_interface(ClientInterface("client_interface", []))
    
    def register_handler(self, platform: Platform, handler: Callable):
        """
        注册消息处理器
        
        Args:
            platform: 消息平台
            handler: 处理函数
        """
        message_handler = MessageHandler(platform=platform, handler=handler)
        
        if platform not in self._handlers:
            self._handlers[platform] = []
        
        self._handlers[platform].append(message_handler)
    
    def unregister_handler(self, platform: Platform, handler: Callable):
        """注销处理器"""
        if platform in self._handlers:
            self._handlers[platform] = [
                h for h in self._handlers[platform] 
                if h.handler != handler
            ]
    
    async def route_message(self, message: Message) -> List[Any]:
        """
        路由消息
        
        Args:
            message: 消息对象
            
        Returns:
            处理结果列表
        """
        # 存储消息
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]
        
        # 应用路由规则
        for rule in self._routing_rules:
            if not rule(message):
                return []
        
        # 获取处理器
        handlers = self._handlers.get(message.platform, [])
        
        # 并发执行所有处理器
        results = []
        for handler in handlers:
            if handler.enabled:
                try:
                    result = await handler.process(message)
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
        
        return results
    
    def send_message(
        self,
        platform: Platform,
        content: str,
        receiver: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        发送消息
        
        Args:
            platform: 目标平台
            content: 消息内容
            receiver: 接收者
            metadata: 附加信息
            
        Returns:
            消息对象
        """
        from . import Message as MsgClass
        import uuid
        
        message = Message(
            id=str(uuid.uuid4()),
            platform=platform,
            content=content,
            sender="agent",
            receiver=receiver,
            metadata=metadata or {}
        )
        
        # 存储消息
        self._message_history.append(message)
        
        return message
    
    def add_routing_rule(self, rule: Callable):
        """添加路由规则"""
        self._routing_rules.append(rule)
    
    def get_history(self, platform: Optional[Platform] = None, limit: int = 100) -> List[Message]:
        """获取消息历史"""
        if platform:
            messages = [m for m in self._message_history if m.platform == platform]
        else:
            messages = self._message_history
        
        return messages[-limit:]
    
    def clear_history(self):
        """清空历史"""
        self._message_history.clear()
    
    def _on_initialize(self):
        # 注册终端处理器
        self.register_handler(Platform.TERMINAL, self._terminal_handler)
    
    async def _terminal_handler(self, message: Message) -> str:
        """终端消息处理"""
        return f"Terminal message received: {message.content}"
    
    def _on_start(self):
        pass
    
    def _on_stop(self):
        pass
