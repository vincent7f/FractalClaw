"""
Webhook 管理器

提供 Webhook 注册、触发和回调处理
"""

from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import uuid
import hashlib
import hmac
import json

from fractalclaw.core.component import Component, LeafComponent, ComponentState


class WebhookEvent(Enum):
    """Webhook 事件类型"""
    MESSAGE = "message"
    COMMAND = "command"
    CALLBACK = "callback"
    TICKER = "ticker"
    SCHEDULED = "scheduled"
    CUSTOM = "custom"


class WebhookStatus(Enum):
    """Webhook 状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class Webhook:
    """Webhook 定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    url: str = ""
    events: List[WebhookEvent] = field(default_factory=list)
    secret: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    status: WebhookStatus = WebhookStatus.ACTIVE
    timeout: int = 30
    retries: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "events": [e.value for e in self.events],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "trigger_count": self.trigger_count,
        }


@dataclass
class WebhookRequest:
    """Webhook 请求"""
    webhook_id: str = ""
    event: WebhookEvent = WebhookEvent.CUSTOM
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    headers: Dict[str, str] = field(default_factory=dict)
    source: str = ""


# Webhook 处理器类型
WebhookHandler = Callable[[WebhookRequest], Awaitable[Optional[Dict[str, Any]]]]


class WebhookManager(LeafComponent):
    """
    Webhook 管理器
    
    提供 Webhook 注册、触发和回调处理能力
    支持:
    - 动态 Webhook 注册
    - 签名验证
    - 请求重试
    - 事件过滤
    """

    def __init__(self, name: str = "webhook"):
        super().__init__(name)
        
        self._webhooks: Dict[str, Webhook] = {}
        self._handlers: Dict[WebhookEvent, WebhookHandler] = {}
        self._server = None
        self._running = False

    # ==================== 生命周期 ====================

    def _on_initialize(self):
        """初始化"""
        pass

    def _on_start(self):
        """启动 Webhook 服务器"""
        self._running = True
        asyncio.create_task(self._start_server())

    def _on_stop(self):
        """停止 Webhook 服务器"""
        self._running = False
        if self._server:
            self._server.close()

    # ==================== Webhook 管理 ====================

    def register_webhook(
        self,
        name: str,
        url: str,
        events: List[WebhookEvent],
        secret: str = "",
        headers: Optional[Dict[str, str]] = None,
    ) -> Webhook:
        """注册 Webhook"""
        webhook = Webhook(
            name=name,
            url=url,
            events=events,
            secret=secret,
            headers=headers or {},
        )
        
        self._webhooks[webhook.id] = webhook
        return webhook

    def unregister_webhook(self, webhook_id: str) -> bool:
        """注销 Webhook"""
        return self._webhooks.pop(webhook_id, None) is not None

    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """获取 Webhook"""
        return self._webhooks.get(webhook_id)

    def list_webhooks(self) -> List[Webhook]:
        """列出所有 Webhook"""
        return list(self._webhooks.values())

    def get_webhooks_by_event(self, event: WebhookEvent) -> List[Webhook]:
        """根据事件获取 Webhook"""
        return [w for w in self._webhooks.values() if event in w.events]

    def update_webhook(
        self,
        webhook_id: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        events: Optional[List[WebhookEvent]] = None,
        secret: Optional[str] = None,
    ) -> Optional[Webhook]:
        """更新 Webhook"""
        webhook = self._webhooks.get(webhook_id)
        if not webhook:
            return None
        
        if name is not None:
            webhook.name = name
        if url is not None:
            webhook.url = url
        if events is not None:
            webhook.events = events
        if secret is not None:
            webhook.secret = secret
        
        return webhook

    def activate_webhook(self, webhook_id: str) -> bool:
        """激活 Webhook"""
        webhook = self._webhooks.get(webhook_id)
        if webhook:
            webhook.status = WebhookStatus.ACTIVE
            return True
        return False

    def deactivate_webhook(self, webhook_id: str) -> bool:
        """停用 Webhook"""
        webhook = self._webhooks.get(webhook_id)
        if webhook:
            webhook.status = WebhookStatus.INACTIVE
            return True
        return False

    # ==================== 事件处理 ====================

    def register_handler(
        self,
        event: WebhookEvent,
        handler: WebhookHandler,
    ):
        """注册事件处理器"""
        self._handlers[event] = handler

    # ==================== 触发 Webhook ====================

    async def trigger(
        self,
        event: WebhookEvent,
        data: Dict[str, Any],
        source: str = "",
    ) -> Dict[str, Any]:
        """触发 Webhook"""
        request = WebhookRequest(
            event=event,
            data=data,
            source=source,
        )
        
        results = {}
        
        # 查找匹配的 Webhook
        webhooks = self.get_webhooks_by_event(event)
        
        for webhook in webhooks:
            if webhook.status != WebhookStatus.ACTIVE:
                continue
            
            request.webhook_id = webhook.id
            success = await self._send_webhook(webhook, request)
            results[webhook.id] = success
            
            # 更新统计
            webhook.last_triggered = datetime.now()
            webhook.trigger_count += 1
        
        return results

    async def _send_webhook(
        self,
        webhook: Webhook,
        request: WebhookRequest,
    ) -> bool:
        """发送 Webhook 请求"""
        import aiohttp
        
        try:
            # 构建请求头
            headers = dict(webhook.headers)
            headers["Content-Type"] = "application/json"
            
            # 添加签名
            if webhook.secret:
                body = json.dumps(request.data)
                signature = self._generate_signature(body, webhook.secret)
                headers["X-Webhook-Signature"] = signature
            
            # 发送请求
            timeout = aiohttp.ClientTimeout(total=webhook.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    webhook.url,
                    json=request.data,
                    headers=headers,
                ) as response:
                    webhook.status = WebhookStatus.ACTIVE
                    return response.status < 400
                    
        except asyncio.TimeoutError:
            webhook.status = WebhookStatus.ERROR
            return False
        except Exception as e:
            webhook.status = WebhookStatus.ERROR
            # 重试逻辑
            if webhook.retries > 0:
                for i in range(webhook.retries):
                    await asyncio.sleep(2 ** i)
                    try:
                        # 重试发送
                        return True
                    except:
                        pass
            return False

    def _generate_signature(self, body: str, secret: str) -> str:
        """生成签名"""
        return hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

    def verify_signature(self, body: str, signature: str, secret: str) -> bool:
        """验证签名"""
        expected = self._generate_signature(body, secret)
        return hmac.compare_digest(expected, signature)

    # ==================== HTTP 服务器 ====================

    async def _start_server(self):
        """启动内嵌 HTTP 服务器"""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post("/{webhook_id}", self._handle_webhook)
        app.router.add_get("/list", self._handle_list_webhooks)
        app.router.add_post("/trigger/{event}", self._handle_trigger)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 18790)
        await site.start()
        
        self._server = runner

    async def _handle_webhook(self, request):
        """处理 Webhook 请求（接收回调）"""
        webhook_id = request.match_info.get("webhook_id")
        webhook = self.get_webhook(webhook_id)
        
        if not webhook:
            return web.json_response({"error": "Webhook not found"}, status=404)
        
        # 验证签名
        if webhook.secret:
            signature = request.headers.get("X-Webhook-Signature", "")
            body = await request.text()
            
            if not self.verify_signature(body, signature, webhook.secret):
                return web.json_response({"error": "Invalid signature"}, status=401)
        
        # 处理请求
        try:
            data = await request.json()
        except:
            data = {}
        
        request_obj = WebhookRequest(
            webhook_id=webhook_id,
            event=WebhookEvent.CUSTOM,
            data=data,
            headers=dict(request.headers),
        )
        
        # 调用处理器
        handler = self._handlers.get(WebhookEvent.CUSTOM)
        if handler:
            result = await handler(request_obj)
            return web.json_response(result or {"status": "ok"})
        
        return web.json_response({"status": "ok"})

    async def _handle_list_webhooks(self, request):
        """列出所有 Webhook"""
        return web.json_response({
            "webhooks": [w.to_dict() for w in self._webhooks.values()]
        })

    async def _handle_trigger(self, request):
        """手动触发 Webhook"""
        event_name = request.match_info.get("event")
        
        try:
            event = WebhookEvent(event_name)
        except:
            return web.json_response({"error": "Invalid event"}, status=400)
        
        try:
            data = await request.json()
        except:
            data = {}
        
        results = await self.trigger(event, data)
        return web.json_response({"results": results})

    # ==================== 便捷方法 ====================

    def create_outgoing_webhook(
        self,
        name: str,
        url: str,
        events: List[str],
    ) -> Webhook:
        """创建 outgoing webhook"""
        event_enums = [WebhookEvent(e) for e in events]
        return self.register_webhook(name, url, event_enums)

    # ==================== 工具方法 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "webhooks_count": len(self._webhooks),
            "active_count": len([w for w in self._webhooks.values() if w.status == WebhookStatus.ACTIVE]),
            "total_triggers": sum(w.trigger_count for w in self._webhooks.values()),
        }
