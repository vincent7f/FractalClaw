"""
Telegram 通道适配器

实现与 Telegram Bot API 的集成
"""

from typing import Dict, List, Any, Optional
import asyncio
import json

from fractalclaw.channels.base import (
    Channel,
    ChannelConfig,
    ChannelState,
    Message,
    MessageType,
)


class TelegramChannel(Channel):
    """
    Telegram 通道适配器
    
    使用 Telegram Bot API 实现消息收发
    """

    def __init__(
        self,
        name: str = "telegram",
        bot_token: str = "",
        config: Optional[ChannelConfig] = None,
    ):
        if config is None:
            config = ChannelConfig(name=name)
        config.extra["bot_token"] = bot_token
        
        super().__init__(name, "telegram", config)
        
        self.bot_token = bot_token
        self.api_base = f"https://api.telegram.org/bot{bot_token}"
        self._update_offset = 0
        self._polling_task: Optional[asyncio.Task] = None

    # ==================== 抽象方法实现 ====================

    async def connect(self) -> bool:
        """建立与 Telegram 的连接"""
        try:
            self.state = ChannelState.CONNECTING
            
            # 验证 bot token
            response = await self._api_request("getMe")
            if not response or not response.get("ok"):
                self.state = ChannelState.ERROR
                return False
            
            self.state = ChannelState.CONNECTED
            await self._on_connect()
            return True
            
        except Exception as e:
            self.state = ChannelState.ERROR
            await self._on_channel_error(e)
            return False

    async def disconnect(self):
        """断开与 Telegram 的连接"""
        self._running = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        self.state = ChannelState.DISCONNECTED
        await self._on_disconnect()

    async def _send_message_impl(self, message: Message) -> bool:
        """发送消息到 Telegram"""
        try:
            chat_id = message.channel_id or message.metadata.get("chat_id")
            if not chat_id:
                return False
            
            params = {
                "chat_id": chat_id,
                "text": message.content,
            }
            
            # 处理回复
            if message.reply_to:
                params["reply_to_message_id"] = message.reply_to
            
            # 处理 Markdown/HTML
            if message.metadata.get("parse_mode"):
                params["parse_mode"] = message.metadata["parse_mode"]
            
            # 处理键盘
            if message.metadata.get("reply_markup"):
                params["reply_markup"] = json.dumps(message.metadata["reply_markup"])
            
            response = await self._api_request("sendMessage", params)
            return response and response.get("ok", False)
            
        except Exception as e:
            await self._on_channel_error(e)
            return False

    async def _receive_message_loop(self):
        """接收消息轮询循环"""
        while self._running:
            try:
                await self._poll_updates()
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._on_channel_error(e)
                await asyncio.sleep(self.config.retry_delay)

    # ==================== Telegram API ====================

    async def _api_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """发送 API 请求到 Telegram"""
        import aiohttp
        
        url = f"{self.api_base}/{method}"
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=params or {}) as response:
                return await response.json()

    async def _poll_updates(self):
        """轮询更新"""
        params = {"timeout": self.config.timeout, "offset": self._update_offset}
        
        response = await self._api_request("getUpdates", params)
        if not response or not response.get("ok"):
            return
        
        updates = response.get("result", [])
        for update in updates:
            await self._process_update(update)
            self._update_offset = update["update_id"] + 1

    async def _process_update(self, update: Dict[str, Any]):
        """处理接收到的更新"""
        if "message" not in update:
            return
        
        msg = update["message"]
        
        message = Message(
            id=str(update["update_id"]),
            channel_id=str(msg["chat"]["id"]),
            channel_type="telegram",
            user_id=str(msg["from"]["id"]) if "from" in msg else "",
            user_name=msg["from"]["first_name"] if "from" in msg else "",
            content=msg.get("text", ""),
            message_type=self._get_message_type(msg),
            metadata={
                "chat_id": msg["chat"]["id"],
                "message_id": msg["message_id"],
                "raw": msg,
            }
        )
        
        # 检测命令
        if message.content.startswith("/"):
            message.message_type = MessageType.COMMAND
        
        await self.handle_message(message)

    def _get_message_type(self, msg: Dict[str, Any]) -> MessageType:
        """根据消息内容判断类型"""
        if "text" in msg:
            return MessageType.TEXT
        elif "photo" in msg:
            return MessageType.IMAGE
        elif "video" in msg:
            return MessageType.VIDEO
        elif "voice" in msg:
            return MessageType.AUDIO
        elif "document" in msg:
            return MessageType.FILE
        return MessageType.TEXT

    # ==================== Telegram 特有功能 ====================

    async def send_photo(
        self,
        chat_id: str,
        photo: str,
        caption: Optional[str] = None,
    ) -> bool:
        """发送图片"""
        params = {"chat_id": chat_id, "photo": photo}
        if caption:
            params["caption"] = caption
        
        response = await self._api_request("sendPhoto", params)
        return response and response.get("ok", False)

    async def send_video(
        self,
        chat_id: str,
        video: str,
        caption: Optional[str] = None,
    ) -> bool:
        """发送视频"""
        params = {"chat_id": chat_id, "video": video}
        if caption:
            params["caption"] = caption
        
        response = await self._api_request("sendVideo", params)
        return response and response.get("ok", False)

    async def send_document(
        self,
        chat_id: str,
        document: str,
        caption: Optional[str] = None,
    ) -> bool:
        """发送文档"""
        params = {"chat_id": chat_id, "document": document}
        if caption:
            params["caption"] = caption
        
        response = await self._api_request("sendDocument", params)
        return response and response.get("ok", False)

    async def send_sticker(
        self,
        chat_id: str,
        sticker: str,
    ) -> bool:
        """发送贴纸"""
        params = {"chat_id": chat_id, "sticker": sticker}
        response = await self._api_request("sendSticker", params)
        return response and response.get("ok", False)

    async def set_webhook(self, webhook_url: str) -> bool:
        """设置 Webhook"""
        params = {"url": webhook_url}
        response = await self._api_request("setWebhook", params)
        return response and response.get("ok", False)

    async def delete_webhook(self) -> bool:
        """删除 Webhook"""
        response = await self._api_request("deleteWebhook")
        return response and response.get("ok", False)

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
    ) -> bool:
        """回答回调查询（内联键盘按钮）"""
        params = {"callback_query_id": callback_query_id}
        if text:
            params["text"] = text
        
        response = await self._api_request("answerCallbackQuery", params)
        return response and response.get("ok", False)

    async def edit_message_text(
        self,
        chat_id: str,
        message_id: int,
        text: str,
        inline_markup: Optional[List[List[Dict]]] = None,
    ) -> bool:
        """编辑消息文本"""
        params = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }
        if inline_markup:
            params["reply_markup"] = json.dumps({"inline_keyboard": inline_markup})
        
        response = await self._api_request("editMessageText", params)
        return response and response.get("ok", False)

    def create_inline_keyboard(
        self,
        buttons: List[List[Dict[str, str]]],
    ) -> Dict[str, Any]:
        """创建内联键盘"""
        return {"inline_keyboard": buttons}
