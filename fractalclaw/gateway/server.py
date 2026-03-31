"""
Gateway 服务器核心

提供 WebSocket 和 HTTP 接口，管理客户端连接和消息路由
"""

from typing import Dict, List, Any, Optional, Callable, Awaitable
import asyncio
import json
import uuid
from datetime import datetime
from dataclasses import dataclass, field

from fractalclaw.core.component import Component, CompositeComponent, ComponentState


@dataclass
class Client:
    """客户端连接"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    channel_type: str = ""
    user_id: str = ""
    user_name: str = ""
    connected_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# 消息处理器类型
MessageHandler = Callable[[Client, Dict[str, Any]], Awaitable[None]]


class GatewayServer(CompositeComponent):
    """
    Gateway 服务器
    
    管理 WebSocket 连接、消息路由、会话管理
    监听端口: 18789
    """

    def __init__(
        self,
        name: str = "gateway",
        host: str = "0.0.0.0",
        port: int = 18789,
    ):
        super().__init__(name)
        
        self.host = host
        self.port = port
        
        self._server: Optional[asyncio.Server] = None
        self._clients: Dict[str, Client] = {}
        self._ws_connections: Dict[str, Any] = {}  # client_id -> websocket
        self._sessions: Dict[str, List[str]] = {}  # session_id -> [client_ids]
        self._handlers: Dict[str, MessageHandler] = {}
        self._running = False
        
        # HTTP 服务器（用于 Webhook）
        self._http_server = None

    # ==================== 生命周期 ====================

    def _on_initialize(self):
        """初始化"""
        self._ws_server = None
        self._http_app = None

    def _on_start(self):
        """启动服务器"""
        # 启动异步任务来运行服务器
        import threading
        import asyncio
        
        def run_async_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._start_servers())
            loop.run_forever()
        
        self._server_thread = threading.Thread(target=run_async_server, daemon=True)
        self._server_thread.start()
        self._running = True

    async def _start_servers(self):
        """异步启动服务器"""
        import websockets
        
        self._ws_server = await websockets.serve(
            self._ws_handler, self.host, self.port
        )
        await self._start_http_server()

    def _on_stop(self):
        """停止服务器"""
        self._running = False
        if hasattr(self, '_server_thread'):
            self._server_thread = None

    # ==================== WebSocket 服务器 ====================

    async def _ws_handler(self, websocket, path):
        """WebSocket 连接处理器"""
        import websockets
        
        client = Client()
        self._clients[client.id] = client
        self._ws_connections[client.id] = websocket
        
        try:
            # 发送连接确认
            await websocket.send(json.dumps({
                "type": "connected",
                "client_id": client.id,
            }))
            
            # 处理消息
            async for raw_message in websocket:
                try:
                    message = json.loads(raw_message)
                    await self._handle_message(websocket, client, message)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON",
                    }))
                except Exception as e:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": str(e),
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._disconnect_client(client.id)

    async def _start_http_server(self):
        """启动 HTTP 服务器（用于 Webhook）"""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post("/webhook/{channel}", self._handle_webhook)
        app.router.add_get("/health", self._handle_health)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port + 1)
        await site.start()
        
        self._http_app = runner

    async def _handle_webhook(self, request):
        """处理 Webhook 请求"""
        channel = request.match_info.get("channel")
        
        try:
            data = await request.json()
        except:
            data = {}
        
        # 查找相关客户端
        clients = self.get_clients_by_channel(channel)
        
        # 广播到相关客户端
        for client in clients:
            await self._broadcast_to_client(client, {
                "type": "webhook",
                "channel": channel,
                "data": data,
            })
        
        return web.json_response({"status": "ok"})

    async def _handle_health(self, request):
        """健康检查"""
        return web.json_response({
            "status": "ok",
            "clients": len(self._clients),
            "sessions": len(self._sessions),
        })

    # ==================== 消息处理 ====================

    async def _handle_message(
        self,
        websocket,
        client: Client,
        message: Dict[str, Any],
    ):
        """处理接收到的消息"""
        msg_type = message.get("type")
        
        # 更新活跃时间
        client.last_active = datetime.now()
        
        if msg_type == "auth":
            # 认证
            client.session_id = message.get("session_id", "")
            client.channel_type = message.get("channel_type", "")
            client.user_id = message.get("user_id", "")
            client.user_name = message.get("user_name", "")
            
            # 加入会话
            if client.session_id:
                if client.session_id not in self._sessions:
                    self._sessions[client.session_id] = []
                self._sessions[client.session_id].append(client.id)
            
            await websocket.send(json.dumps({
                "type": "auth_ok",
                "client_id": client.id,
                "session_id": client.session_id,
            }))
            
        elif msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))
            
        elif msg_type == "message":
            # 处理聊天消息
            handler = self._handlers.get("message")
            if handler:
                await handler(client, message)
                
        elif msg_type == "join_session":
            # 加入会话
            session_id = message.get("session_id")
            if session_id:
                client.session_id = session_id
                if session_id not in self._sessions:
                    self._sessions[session_id] = []
                if client.id not in self._sessions[session_id]:
                    self._sessions[session_id].append(client.id)
                    
        elif msg_type == "leave_session":
            # 离开会话
            session_id = message.get("session_id")
            if session_id and session_id in self._sessions:
                if client.id in self._sessions[session_id]:
                    self._sessions[session_id].remove(client.id)
                client.session_id = ""
        
        # 调用注册的处理器
        handler = self._handlers.get(msg_type)
        if handler:
            await handler(client, message)

    def register_handler(self, event: str, handler: MessageHandler):
        """注册消息处理器"""
        self._handlers[event] = handler

    def unregister_handler(self, event: str):
        """注销消息处理器"""
        self._handlers.pop(event, None)

    # ==================== 客户端管理 ====================

    def _disconnect_client(self, client_id: str):
        """断开客户端连接"""
        client = self._clients.pop(client_id, None)
        self._ws_connections.pop(client_id, None)
        if client and client.session_id:
            if client.session_id in self._sessions:
                if client.id in self._sessions[client.session_id]:
                    self._sessions[client.session_id].remove(client.id)

    def get_client(self, client_id: str) -> Optional[Client]:
        """获取客户端"""
        return self._clients.get(client_id)

    def get_clients_by_session(self, session_id: str) -> List[Client]:
        """获取会话中的所有客户端"""
        client_ids = self._sessions.get(session_id, [])
        return [self._clients[cid] for cid in client_ids if cid in self._clients]

    def get_clients_by_channel(self, channel_type: str) -> List[Client]:
        """获取指定渠道的所有客户端"""
        return [
            c for c in self._clients.values()
            if c.channel_type == channel_type
        ]

    def list_clients(self) -> List[Client]:
        """列出所有客户端"""
        return list(self._clients.values())

    # ==================== 消息发送 ====================

    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """发送消息到指定客户端"""
        # 需要 WebSocket 连接引用，这里简化处理
        # 实际实现需要维护 WebSocket 连接引用
        pass

    async def broadcast_to_session(
        self,
        session_id: str,
        message: Dict[str, Any],
        exclude: Optional[List[str]] = None,
    ):
        """广播消息到会话中的所有客户端"""
        clients = self.get_clients_by_session(session_id)
        exclude = exclude or []
        
        for client in clients:
            if client.id not in exclude:
                await self._broadcast_to_client(client, message)

    async def broadcast_to_channel(
        self,
        channel_type: str,
        message: Dict[str, Any],
    ):
        """广播消息到指定渠道的所有客户端"""
        clients = self.get_clients_by_channel(channel_type)
        
        for client in clients:
            await self._broadcast_to_client(client, message)

    async def broadcast_to_all(
        self,
        message: Dict[str, Any],
    ):
        """广播消息到所有客户端"""
        for client in self._clients.values():
            await self._broadcast_to_client(client, message)

    async def _broadcast_to_client(self, client: Client, message: Dict[str, Any]):
        """向客户端发送消息（内部方法）"""
        websocket = self._ws_connections.get(client.id)
        if websocket:
            try:
                message["client_id"] = client.id
                await websocket.send(json.dumps(message))
            except Exception:
                pass  # Connection may have closed

    # ==================== 工具方法 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取服务器统计信息"""
        return {
            "host": self.host,
            "port": self.port,
            "clients": len(self._clients),
            "sessions": len(self._sessions),
            "running": self._running,
        }


class SessionManager:
    """
    会话管理器
    
    管理代理会话的生命周期
    """

    def __init__(self, gateway: GatewayServer):
        self.gateway = gateway
        self._agents: Dict[str, Any] = {}  # session_id -> agent

    def create_session(
        self,
        session_id: str,
        agent: Any = None,
    ) -> str:
        """创建新会话"""
        if session_id in self._agents:
            return session_id
        
        self._agents[session_id] = agent
        return session_id

    def get_session(self, session_id: str) -> Optional[Any]:
        """获取会话代理"""
        return self._agents.get(session_id)

    def remove_session(self, session_id: str):
        """移除会话"""
        self._agents.pop(session_id, None)

    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        return list(self._agents.keys())

    async def send_to_agent(self, session_id: str, message: Dict[str, Any]):
        """发送消息到代理"""
        agent = self._agents.get(session_id)
        if agent and hasattr(agent, "process_message"):
            await agent.process_message(message)
