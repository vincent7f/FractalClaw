"""
消息路由器

根据规则将消息路由到对应的代理或处理程序
"""

from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import re
import hashlib

from fractalclaw.channels.base import Message, Channel
from fractalclaw.gateway.server import Client, GatewayServer


class RouteStrategy(Enum):
    """路由策略"""
    SESSION = "session"          # 按会话隔离
    ROUND_ROBIN = "round_robin"  # 轮询
    LOAD_BALANCE = "load_balance"  # 负载均衡
    BROADCAST = "broadcast"      # 广播


@dataclass
class RouteRule:
    """路由规则"""
    name: str
    channel_type: str = ""
    pattern: str = ""  # 消息内容匹配
    user_id: str = ""   # 用户ID匹配
    priority: int = 0   # 优先级（越高越先匹配）
    
    def matches(self, message: Message) -> bool:
        """检查消息是否匹配规则"""
        # 检查渠道类型
        if self.channel_type and message.channel_type != self.channel_type:
            return False
        
        # 检查用户ID
        if self.user_id and message.user_id != self.user_id:
            return False
        
        # 检查内容模式
        if self.pattern:
            try:
                if not re.search(self.pattern, message.content):
                    return False
            except re.error:
                return False
        
        return True


@dataclass
class RouteTarget:
    """路由目标"""
    type: str  # "agent", "channel", "webhook", "function"
    name: str
    config: Dict[str, Any] = field(default_factory=dict)


# 路由处理器类型
RouteHandler = Callable[[Message], Awaitable[Optional[Message]]]


class MessageRouter:
    """
    消息路由器
    
    根据规则将消息路由到不同的处理程序
    支持:
    - 多代理隔离
    - 消息过滤
    - 会话管理
    """

    def __init__(
        self,
        gateway: GatewayServer,
        default_session_ttl: int = 3600,
    ):
        self.gateway = gateway
        self.default_session_ttl = default_session_ttl
        
        self._rules: List[RouteRule] = []
        self._targets: Dict[str, RouteTarget] = {}
        self._handlers: Dict[str, RouteHandler] = {}
        self._session_routes: Dict[str, str] = {}  # client_id -> agent_name
        self._round_robin_index: Dict[str, int] = {}
        
        # 注册默认处理器
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册默认处理器"""
        self.register_handler("agent", self._route_to_agent)
        self.register_handler("channel", self._route_to_channel)
        self.register_handler("webhook", self._route_to_webhook)

    # ==================== 规则管理 ====================

    def add_rule(self, rule: RouteRule):
        """添加路由规则"""
        self._rules.append(rule)
        # 按优先级排序
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, name: str):
        """移除路由规则"""
        self._rules = [r for r in self._rules if r.name != name]

    def clear_rules(self):
        """清空所有规则"""
        self._rules.clear()

    def list_rules(self) -> List[RouteRule]:
        """列出所有规则"""
        return self._rules.copy()

    # ==================== 目标管理 ====================

    def add_target(self, target: RouteTarget):
        """添加路由目标"""
        self._targets[target.name] = target

    def remove_target(self, name: str):
        """移除路由目标"""
        self._targets.pop(name, None)

    def get_target(self, name: str) -> Optional[RouteTarget]:
        """获取路由目标"""
        return self._targets.get(name)

    def list_targets(self) -> List[RouteTarget]:
        """列出所有目标"""
        return list(self._targets.values())

    # ==================== 处理器管理 ====================

    def register_handler(self, handler_type: str, handler: RouteHandler):
        """注册路由处理器"""
        self._handlers[handler_type] = handler

    # ==================== 路由核心 ====================

    async def route_message(self, message: Message) -> Optional[Message]:
        """路由消息"""
        # 查找匹配的规则
        for rule in self._rules:
            if rule.matches(message):
                target = self._targets.get(rule.name)
                if target:
                    handler = self._handlers.get(target.type)
                    if handler:
                        return await handler(message)
        
        return None

    async def route_to_session(
        self,
        message: Message,
        session_id: str,
        agent_name: str = "default",
    ) -> Optional[Message]:
        """路由到指定会话"""
        # 保存会话路由
        self._session_routes[message.metadata.get("client_id", "")] = agent_name
        
        # 发送到网关
        await self.gateway.broadcast_to_session(session_id, {
            "type": "message",
            "message": message.to_dict(),
            "agent": agent_name,
        })
        
        return message

    async def create_session_for_channel(
        self,
        message: Message,
        agent_name: str = "default",
    ) -> str:
        """为渠道创建会话"""
        # 基于渠道信息生成会话ID
        session_hash = hashlib.md5(
            f"{message.channel_type}:{message.channel_id}".encode()
        ).hexdigest()[:8]
        
        session_id = f"{message.channel_type}_{session_hash}"
        
        # 保存路由关系
        self._session_routes[message.metadata.get("client_id", "")] = session_id
        
        return session_id

    # ==================== 默认处理器 ====================

    async def _route_to_agent(
        self,
        message: Message,
    ) -> Optional[Message]:
        """路由到代理"""
        # 发送到代理处理
        return message

    async def _route_to_channel(
        self,
        message: Message,
    ) -> Optional[Message]:
        """路由到其他渠道"""
        channel_name = message.metadata.get("forward_to")
        channel = self.gateway.get_child(channel_name)
        
        if channel and isinstance(channel, Channel):
            await channel.send_message(message)
        
        return message

    async def _route_to_webhook(
        self,
        message: Message,
    ) -> Optional[Message]:
        """路由到 Webhook"""
        webhook_url = message.metadata.get("webhook_url")
        if webhook_url:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                await session.post(webhook_url, json=message.to_dict())
        
        return message

    # ==================== 高级路由 ====================

    async def route_with_strategy(
        self,
        message: Message,
        strategy: RouteStrategy,
        agent_names: List[str],
    ) -> Optional[Message]:
        """使用指定策略路由"""
        if strategy == RouteStrategy.SESSION:
            # 会话隔离
            session_id = self.get_or_create_session(message)
            return await self.route_to_session(message, session_id)
        
        elif strategy == RouteStrategy.ROUND_ROBIN:
            # 轮询
            agent_name = self._round_robin(agent_names)
            message.metadata["agent"] = agent_name
            return message
        
        elif strategy == RouteStrategy.LOAD_BALANCE:
            # 负载均衡（选择负载最小的）
            agent_name = await self._load_balance(agent_names)
            message.metadata["agent"] = agent_name
            return message
        
        elif strategy == RouteStrategy.BROADCAST:
            # 广播到所有
            for agent_name in agent_names:
                msg_copy = Message(**message.to_dict())
                msg_copy.metadata["agent"] = agent_name
                await self.gateway.broadcast_to_all({
                    "type": "message",
                    "message": msg_copy.to_dict(),
                })
            return message
        
        return None

    def _round_robin(self, agent_names: List[str]) -> str:
        """轮询选择"""
        key = ",".join(agent_names)
        index = self._round_robin_index.get(key, 0)
        
        selected = agent_names[index % len(agent_names)]
        self._round_robin_index[key] = (index + 1) % len(agent_names)
        
        return selected

    async def _load_balance(self, agent_names: List[str]) -> str:
        """负载均衡选择"""
        # 简化实现：选择会话数最少的
        min_sessions = float("inf")
        selected = agent_names[0]
        
        for name in agent_names:
            session_count = len([
                s for s in self._session_routes.values()
                if s == name
            ])
            if session_count < min_sessions:
                min_sessions = session_count
                selected = name
        
        return selected

    def get_or_create_session(self, message: Message) -> str:
        """获取或创建会话"""
        client_id = message.metadata.get("client_id", "")
        
        if client_id in self._session_routes:
            return self._session_routes[client_id]
        
        # 创建新会话
        session_id = self.create_session_for_channel(message)
        return session_id

    # ==================== 工具方法 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取路由统计"""
        return {
            "rules_count": len(self._rules),
            "targets_count": len(self._targets),
            "session_routes_count": len(self._session_routes),
        }
