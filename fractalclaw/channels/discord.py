"""
Discord 通道适配器

实现与 Discord API 的集成
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


class DiscordChannel(Channel):
    """
    Discord 通道适配器
    
    使用 Discord HTTP API 和 Gateway 实现消息收发
    支持: 文本消息、Embed、组件交互、斜杠命令
    """

    def __init__(
        self,
        name: str = "discord",
        bot_token: str = "",
        config: Optional[ChannelConfig] = None,
    ):
        if config is None:
            config = ChannelConfig(name=name)
        config.extra["bot_token"] = bot_token
        
        super().__init__(name, "discord", config)
        
        self.bot_token = bot_token
        self.api_base = "https://discord.com/api/v10"
        self._session: Optional[Any] = None
        self._running = False

    # ==================== 抽象方法实现 ====================

    async def connect(self) -> bool:
        """建立与 Discord 的连接"""
        try:
            self.state = ChannelState.CONNECTING
            
            # 验证 token
            response = await self._api_request("users/@me")
            if not response or "id" not in response:
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
        """断开与 Discord 的连接"""
        self._running = False
        if self._session:
            await self._session.close()
            self._session = None
        self.state = ChannelState.DISCONNECTED
        await self._on_disconnect()

    async def _send_message_impl(self, message: Message) -> bool:
        """发送消息到 Discord"""
        try:
            channel_id = message.channel_id
            if not channel_id:
                return False
            
            params: Dict[str, Any] = {
                "content": message.content,
            }
            
            # 处理 Embed
            if message.metadata.get("embed"):
                params["embeds"] = [message.metadata["embed"]]
            
            # 处理组件
            if message.metadata.get("components"):
                params["components"] = message.metadata["components"]
            
            # 处理回复
            if message.reply_to:
                params["message_reference"] = {"message_id": message.reply_to}
            
            # 处理 TTS
            if message.metadata.get("tts"):
                params["tts"] = True
            
            response = await self._api_request(
                f"channels/{channel_id}/messages",
                method="POST",
                params=params,
            )
            
            return response and "id" in response
            
        except Exception as e:
            await self._on_channel_error(e)
            return False

    async def _receive_message_loop(self):
        """接收消息循环 - 由外部 Webhook/网关驱动"""
        # Discord 主要通过 Gateway (WebSocket) 或 HTTP Webhook 接收消息
        pass

    # ==================== Discord API ====================

    async def _api_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """发送 API 请求到 Discord"""
        import aiohttp
        
        url = f"{self.api_base}/{endpoint}"
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
        }
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, url, json=params or {}, headers=headers) as response:
                if response.status == 204:
                    return {"ok": True}
                return await response.json()

    # ==================== Discord 事件处理 ====================

    async def handle_interaction(self, interaction: Dict[str, Any]) -> Optional[Message]:
        """处理交互（按钮、下拉菜单等）"""
        interaction_type = interaction.get("type")
        
        if interaction_type == 2:  # 斜杠命令
            return await self._process_slash_command(interaction)
        elif interaction_type == 3:  # 组件交互
            return await self._process_component_interaction(interaction)
        
        return None

    async def _process_slash_command(self, interaction: Dict[str, Any]) -> Message:
        """处理斜杠命令"""
        data = interaction.get("data", {})
        options = data.get("options", [])
        
        # 构建命令内容
        command_name = data.get("name", "")
        args = " ".join([f"{opt.get('name')}={opt.get('value')}" for opt in options])
        
        message = Message(
            id=interaction.get("id", ""),
            channel_id=str(interaction.get("channel_id", "")),
            channel_type="discord",
            user_id=interaction.get("member", {}).get("user", {}).get("id", ""),
            user_name=interaction.get("member", {}).get("nick") or interaction.get("member", {}).get("user", {}).get("username", ""),
            content=f"/{command_name} {args}",
            message_type=MessageType.COMMAND,
            metadata={
                "interaction_id": interaction.get("id"),
                "token": interaction.get("token"),
                "data": data,
                "raw": interaction,
            }
        )
        
        await self.handle_message(message)
        return message

    async def _process_component_interaction(self, interaction: Dict[str, Any]) -> Message:
        """处理组件交互（按钮、选择菜单）"""
        data = interaction.get("data", {})
        
        message = Message(
            id=interaction.get("id", ""),
            channel_id=str(interaction.get("channel_id", "")),
            channel_type="discord",
            user_id=interaction.get("member", {}).get("user", {}).get("id", ""),
            content=data.get("custom_id", ""),
            message_type=MessageType.COMMAND,
            metadata={
                "interaction_id": interaction.get("id"),
                "token": interaction.get("token"),
                "component_type": data.get("component_type"),
                "custom_id": data.get("custom_id"),
                "values": data.get("values", []),
                "raw": interaction,
            }
        )
        
        await self.handle_message(message)
        return message

    def verify_request(
        self,
        signature: str,
        timestamp: str,
        body: str,
    ) -> bool:
        """验证 Discord 请求签名"""
        import hmac
        import hashlib
        
        if not self.config.extra.get("public_key"):
            return True
        
        public_key = self.config.extra["public_key"]
        
        message = timestamp.encode() + body.encode()
        key = bytes.fromhex(public_key)
        
        expected = hmac.new(key, message, hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(signature, expected)

    # ==================== Discord 特有功能 ====================

    async def send_embed(
        self,
        channel_id: str,
        embed: Dict[str, Any],
    ) -> bool:
        """发送 Embed 消息"""
        params = {"embeds": [embed]}
        response = await self._api_request(
            f"channels/{channel_id}/messages",
            method="POST",
            params=params,
        )
        return response and "id" in response

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
    ) -> bool:
        """编辑消息"""
        params = {"content": content}
        response = await self._api_request(
            f"channels/{channel_id}/messages/{message_id}",
            method="PATCH",
            params=params,
        )
        return response and "id" in response

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> bool:
        """删除消息"""
        response = await self._api_request(
            f"channels/{channel_id}/messages/{message_id}",
            method="DELETE",
        )
        return response is not None

    async def send_interaction_response(
        self,
        interaction_token: str,
        content: str,
        ephemeral: bool = False,
    ) -> bool:
        """发送交互响应"""
        params = {
            "type": 4,  # ChannelMessageWithSource
            "data": {
                "content": content,
            }
        }
        
        if ephemeral:
            params["data"]["flags"] = 64  # Ephemeral
        
        response = await self._api_request(
            f"interactions/{interaction_token}/callback",
            method="POST",
            params=params,
        )
        return response is not None

    async def create_webhook(
        self,
        channel_id: str,
        name: str,
        avatar: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """创建 Webhook"""
        params = {"name": name}
        if avatar:
            params["avatar"] = avatar
        
        response = await self._api_request(
            f"channels/{channel_id}/webhooks",
            method="POST",
            params=params,
        )
        return response if response and "id" in response else None

    def create_embed(
        self,
        title: str = "",
        description: str = "",
        color: int = 0,
        url: str = "",
        footer: Optional[Dict[str, str]] = None,
        image: Optional[Dict[str, str]] = None,
        thumbnail: Optional[Dict[str, str]] = None,
        author: Optional[Dict[str, str]] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """创建 Embed"""
        embed = {
            "title": title,
            "description": description,
            "color": color,
        }
        
        if url:
            embed["url"] = url
        if footer:
            embed["footer"] = footer
        if image:
            embed["image"] = image
        if thumbnail:
            embed["thumbnail"] = thumbnail
        if author:
            embed["author"] = author
        if fields:
            embed["fields"] = fields
        
        return embed

    def create_action_row(
        self,
        components: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """创建操作行（按钮、下拉菜单）"""
        return {
            "type": 1,
            "components": components,
        }

    def create_button(
        self,
        style: int,
        custom_id: str,
        label: str = "",
        emoji: Optional[Dict[str, Any]] = None,
        url: str = "",
        disabled: bool = False,
    ) -> Dict[str, Any]:
        """创建按钮"""
        button = {
            "type": 2,  # Button
            "style": style,
            "custom_id": custom_id,
        }
        
        if label:
            button["label"] = label
        if emoji:
            button["emoji"] = emoji
        if url:
            button["url"] = url
        if disabled:
            button["disabled"] = disabled
        
        return button

    def create_select_menu(
        self,
        custom_id: str,
        placeholder: str = "",
        options: Optional[List[Dict[str, Any]]] = None,
        min_values: int = 1,
        max_values: int = 1,
    ) -> Dict[str, Any]:
        """创建选择菜单"""
        return {
            "type": 3,  # Select Menu
            "custom_id": custom_id,
            "placeholder": placeholder,
            "options": options or [],
            "min_values": min_values,
            "max_values": max_values,
        }
