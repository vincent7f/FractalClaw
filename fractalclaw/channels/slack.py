"""
Slack 通道适配器

实现与 Slack API 的集成
"""

from typing import Dict, List, Any, Optional
import asyncio
import hashlib
import hmac
import json
import time

from fractalclaw.channels.base import (
    Channel,
    ChannelConfig,
    ChannelState,
    Message,
    MessageType,
)


class SlackChannel(Channel):
    """
    Slack 通道适配器
    
    使用 Slack Web API 和 Events API 实现消息收发
    支持: Bot 消息、用户消息、斜杠命令、Webhook
    """

    def __init__(
        self,
        name: str = "slack",
        bot_token: str = "",
        signing_secret: str = "",
        config: Optional[ChannelConfig] = None,
    ):
        if config is None:
            config = ChannelConfig(name=name)
        config.extra["bot_token"] = bot_token
        config.extra["signing_secret"] = signing_secret
        
        super().__init__(name, "slack", config)
        
        self.bot_token = bot_token
        self.signing_secret = signing_secret
        self.api_base = "https://slack.com/api"
        self._running = False

    # ==================== 抽象方法实现 ====================

    async def connect(self) -> bool:
        """建立与 Slack 的连接"""
        try:
            self.state = ChannelState.CONNECTING
            
            # 验证 token
            response = await self._api_request("auth.test")
            if not response or not response.get("ok"):
                self.state = ChannelState.ERROR
                return False
            
            self._running = True
            self.state = ChannelState.CONNECTED
            await self._on_connect()
            return True
            
        except Exception as e:
            self.state = ChannelState.ERROR
            await self._on_channel_error(e)
            return False

    async def disconnect(self):
        """断开与 Slack 的连接"""
        self._running = False
        self.state = ChannelState.DISCONNECTED
        await self._on_disconnect()

    async def _send_message_impl(self, message: Message) -> bool:
        """发送消息到 Slack"""
        try:
            channel = message.channel_id
            if not channel:
                return False
            
            blocks = message.metadata.get("blocks")
            
            params = {
                "channel": channel,
                "text": message.content,
            }
            
            if message.reply_to:
                params["thread_ts"] = message.reply_to
            
            if blocks:
                params["blocks"] = blocks if isinstance(blocks, str) else json.dumps(blocks)
            
            response = await self._api_request("chat.postMessage", params)
            return response and response.get("ok", False)
            
        except Exception as e:
            await self._on_channel_error(e)
            return False

    async def _receive_message_loop(self):
        """接收消息循环 - 由外部事件驱动"""
        # Slack 主要通过 WebSocket (rtm) 或 HTTP Webhook 接收消息
        # 子类可以重写此方法实现 RTM
        pass

    # ==================== Slack API ====================

    async def _api_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """发送 API 请求到 Slack"""
        import aiohttp
        
        url = f"{self.api_base}/{method}"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=params or {}, headers=headers) as response:
                return await response.json()

    # ==================== Slack 事件处理 ====================

    def verify_request(
        self,
        timestamp: str,
        body: str,
        signature: str,
    ) -> bool:
        """验证 Slack 请求签名"""
        if not self.signing_secret:
            return True
        
        # 检查时间戳，防止重放攻击
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False
        
        # 计算签名
        base_string = f"v0:{timestamp}:{body}".encode()
        signing = f"v0={hmac.new(self.signing_secret.encode(), base_string, hashlib.sha256).hexdigest()}"
        
        return hmac.compare_digest(signing, signature)

    async def handle_event(self, event: Dict[str, Any]) -> Optional[Message]:
        """处理 Slack 事件"""
        event_type = event.get("type")
        
        if event_type == "message":
            return await self._process_message_event(event)
        elif event_type == "app_mention":
            return await self._process_mention_event(event)
        
        return None

    async def _process_message_event(self, event: Dict[str, Any]) -> Message:
        """处理消息事件"""
        # 忽略消息变更事件
        if event.get("subtype") in ["message_changed", "message_deleted"]:
            return None
        
        message = Message(
            id=event.get("client_msg_id", event.get("ts", "")),
            channel_id=event.get("channel", ""),
            channel_type="slack",
            user_id=event.get("user", ""),
            content=event.get("text", ""),
            message_type=MessageType.TEXT,
            metadata={
                "ts": event.get("ts"),
                "thread_ts": event.get("thread_ts"),
                "channel": event.get("channel"),
                "raw": event,
            }
        )
        
        # 检测命令
        if message.content.startswith("/"):
            message.message_type = MessageType.COMMAND
        
        await self.handle_message(message)
        return message

    async def _process_mention_event(self, event: Dict[str, Any]) -> Message:
        """处理 @mention 事件"""
        message = Message(
            id=event.get("ts", ""),
            channel_id=event.get("channel", ""),
            channel_type="slack",
            user_id=event.get("user", ""),
            content=event.get("text", ""),
            message_type=MessageType.TEXT,
            metadata={
                "ts": event.get("ts"),
                "thread_ts": event.get("thread_ts"),
                "raw": event,
            }
        )
        
        await self.handle_message(message)
        return message

    async def handle_slash_command(
        self,
        command: str,
        text: str,
        user_id: str,
        channel_id: str,
        response_url: str,
    ) -> Dict[str, Any]:
        """处理斜杠命令"""
        message = Message(
            channel_id=channel_id,
            channel_type="slack",
            user_id=user_id,
            content=f"/{command} {text}",
            message_type=MessageType.COMMAND,
            metadata={
                "command": command,
                "text": text,
                "response_url": response_url,
            }
        )
        
        await self.handle_message(message)
        
        # 返回响应（立即响应）
        return {"response_type": "in_channel"}

    # ==================== Slack 特有功能 ====================

    async def send_thread_reply(
        self,
        channel: str,
        thread_ts: str,
        text: str,
    ) -> bool:
        """发送线程回复"""
        params = {
            "channel": channel,
            "text": text,
            "thread_ts": thread_ts,
        }
        response = await self._api_request("chat.postMessage", params)
        return response and response.get("ok", False)

    async def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
    ) -> bool:
        """更新消息"""
        params = {
            "channel": channel,
            "ts": ts,
            "text": text,
        }
        response = await self._api_request("chat.update", params)
        return response and response.get("ok", False)

    async def delete_message(
        self,
        channel: str,
        ts: str,
    ) -> bool:
        """删除消息"""
        params = {
            "channel": channel,
            "ts": ts,
        }
        response = await self._api_request("chat.delete", params)
        return response and response.get("ok", False)

    async def open_modal(
        self,
        trigger_id: str,
        view: Dict[str, Any],
    ) -> bool:
        """打开模态窗口"""
        params = {
            "trigger_id": trigger_id,
            "view": json.dumps(view),
        }
        response = await self._api_request("views.open", params)
        return response and response.get("ok", False)

    async def post_ephemeral(
        self,
        channel: str,
        user: str,
        text: str,
    ) -> bool:
        """发送临时消息（仅指定用户可见）"""
        params = {
            "channel": channel,
            "user": user,
            "text": text,
        }
        response = await self._api_request("chat.postEphemeral", params)
        return response and response.get("ok", False)

    def create_block_kit_message(
        self,
        text: str,
        blocks: Optional[List[Dict]] = None,
        attachments: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """创建 Block Kit 消息"""
        message = {"text": text}
        if blocks:
            message["blocks"] = blocks
        if attachments:
            message["attachments"] = attachments
        return message

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        params = {"user": user_id}
        response = await self._api_request("users.info", params)
        if response and response.get("ok"):
            return response.get("user")
        return None

    async def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """获取频道信息"""
        params = {"channel": channel_id}
        response = await self._api_request("conversations.info", params)
        if response and response.get("ok"):
            return response.get("channel")
        return None
