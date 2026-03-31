"""
通道基类 - 统一的消息通信接口

支持多渠道集成：Telegram, Slack, Discord, WebSocket 等
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import uuid

from fractalclaw.core.component import Component, LeafComponent, ComponentState, ComponentMetadata
from fractalclaw.core.component import ServiceInterface, ClientInterface


class MessageType(Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    COMMAND = "command"
    SYSTEM = "system"


class ChannelState(Enum):
    """通道状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class Message:
    """统一消息结构"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str = ""
    channel_type: str = ""
    user_id: str = ""
    user_name: str = ""
    content: str = ""
    message_type: MessageType = MessageType.TEXT
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None  # 回复的消息ID

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "channel_type": self.channel_type,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "content": self.content,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "reply_to": self.reply_to,
        }


@dataclass
class ChannelConfig:
    """通道配置"""
    name: str = ""
    enabled: bool = True
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit: Optional[int] = None  # 每秒消息数限制
    extra: Dict[str, Any] = field(default_factory=dict)


# 消息处理器类型
MessageHandler = Callable[[Message], Awaitable[None]]


class Channel(LeafComponent):
    """
    通道基类 - 统一的消息通信接口
    
    抽象了不同通信平台（Telegram, Slack, Discord 等）的差异，
    提供统一的消息收发接口。
    
    服务接口:
    - messaging: 消息发送服务
    - event: 事件处理服务
    
    客户端接口:
    - message_handler: 消息处理器依赖
    """

    def __init__(
        self,
        name: str,
        channel_type: str,
        config: Optional[ChannelConfig] = None,
    ):
        super().__init__(name)
        self.channel_type = channel_type
        self.config = config or ChannelConfig(name=name)
        self._state = ChannelState.DISCONNECTED
        self._handlers: Dict[str, MessageHandler] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None
        
        # 注册服务接口
        self._register_interfaces()

    def _register_interfaces(self):
        """注册接口"""
        # 服务接口
        self.add_interface(ServiceInterface("messaging", [
            "send_message", "send_text", "send_image", "send_file"
        ]))
        self.add_interface(ServiceInterface("event", [
            "on_message", "on_connect", "on_disconnect", "on_error"
        ]))
        
        # 客户端接口
        self.add_interface(ClientInterface("message_handler"))

    @property
    def state(self) -> ChannelState:
        return self._state

    @state.setter
    def state(self, value: ChannelState):
        self._state = value

    # ==================== 消息处理 ====================

    def register_handler(self, event: str, handler: MessageHandler):
        """注册事件处理器"""
        self._handlers[event] = handler

    def unregister_handler(self, event: str):
        """注销事件处理器"""
        self._handlers.pop(event, None)

    async def handle_message(self, message: Message):
        """处理接收到的消息"""
        # 调用注册的处理器
        handler = self._handlers.get("message")
        if handler:
            try:
                await handler(message)
            except Exception as e:
                await self._on_handler_error(e, message)

    async def _on_handler_error(self, error: Exception, message: Message):
        """处理处理器错误"""
        error_handler = self._handlers.get("error")
        if error_handler:
            await error_handler(error, message)

    # ==================== 消息发送接口 ====================

    async def send_message(self, message: Message) -> bool:
        """
        发送消息
        
        Args:
            message: 消息对象
            
        Returns:
            是否发送成功
        """
        return await self._send_message_impl(message)

    async def send_text(self, channel_id: str, text: str, **kwargs) -> bool:
        """发送文本消息的便捷方法"""
        message = Message(
            channel_id=channel_id,
            channel_type=self.channel_type,
            content=text,
            message_type=MessageType.TEXT,
            **kwargs
        )
        return await self.send_message(message)

    async def send_image(self, channel_id: str, image_url: str, **kwargs) -> bool:
        """发送图片消息的便捷方法"""
        message = Message(
            channel_id=channel_id,
            channel_type=self.channel_type,
            content=image_url,
            message_type=MessageType.IMAGE,
            **kwargs
        )
        return await self.send_message(message)

    async def send_file(self, channel_id: str, file_path: str, **kwargs) -> bool:
        """发送文件消息的便捷方法"""
        message = Message(
            channel_id=channel_id,
            channel_type=self.channel_type,
            content=file_path,
            message_type=MessageType.FILE,
            **kwargs
        )
        return await self.send_message(message)

    # ==================== 生命周期方法 ====================

    def _on_initialize(self):
        """初始化"""
        self.state = ChannelState.DISCONNECTED

    def _on_start(self):
        """启动连接"""
        self._running = True

    def _on_stop(self):
        """停止连接"""
        self._running = False

    # ==================== 抽象方法 - 子类实现 ====================

    @abstractmethod
    async def _send_message_impl(self, message: Message) -> bool:
        """
        发送消息的具体实现
        
        子类必须实现此方法
        """
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """
        建立连接
        
        子类必须实现此方法
        """
        pass

    @abstractmethod
    async def disconnect(self):
        """
        断开连接
        
        子类必须实现此方法
        """
        pass

    @abstractmethod
    async def _receive_message_loop(self):
        """
        接收消息循环
        
        子类必须实现此方法
        """
        pass

    # ==================== 事件钩子 ====================

    async def _on_connect(self):
        """连接成功事件"""
        handler = self._handlers.get("connect")
        if handler:
            await handler()

    async def _on_disconnect(self):
        """断开连接事件"""
        handler = self._handlers.get("disconnect")
        if handler:
            await handler()

    async def _on_channel_error(self, error: Exception):
        """错误事件"""
        handler = self._handlers.get("error")
        if handler:
            await handler(error)

    # ==================== 工具方法 ====================

    def get_channel_info(self) -> Dict[str, Any]:
        """获取通道信息"""
        return {
            "name": self.name,
            "type": self.channel_type,
            "state": self.state.value,
            "config": {
                "enabled": self.config.enabled,
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries,
            }
        }

    async def start_listening(self):
        """开始监听消息"""
        if not self._running:
            await self.connect()
        
        self._listen_task = asyncio.create_task(self._receive_message_loop())

    async def stop_listening(self):
        """停止监听消息"""
        self._running = False
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        await self.disconnect()


class ChannelGroup(LeafComponent):
    """
    通道组 - 管理多个通道
    
    用于统一管理多个通信渠道
    """

    def __init__(self, name: str):
        super().__init__(name)
        self._channels: Dict[str, Channel] = {}

    def add_channel(self, channel: Channel) -> Channel:
        """添加通道"""
        self._channels[channel.name] = channel
        return channel

    def remove_channel(self, name: str) -> Optional[Channel]:
        """移除通道"""
        return self._channels.pop(name, None)

    def get_channel(self, name: str) -> Optional[Channel]:
        """获取通道"""
        return self._channels.get(name)

    def list_channels(self) -> List[Channel]:
        """列出所有通道"""
        return list(self._channels.values())

    def get_channel_by_type(self, channel_type: str) -> Optional[Channel]:
        """根据类型获取通道"""
        for channel in self._channels.values():
            if channel.channel_type == channel_type:
                return channel
        return None

    async def broadcast(self, message: Message) -> Dict[str, bool]:
        """广播消息到所有通道"""
        results = {}
        for channel in self._channels.values():
            if channel.config.enabled and channel.state == ChannelState.CONNECTED:
                results[channel.name] = await channel.send_message(message)
        return results

    async def start_all(self):
        """启动所有通道"""
        for channel in self._channels.values():
            if channel.config.enabled:
                await channel.start_listening()

    async def stop_all(self):
        """停止所有通道"""
        for channel in self._channels.values():
            await channel.stop_listening()
