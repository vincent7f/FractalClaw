"""
FractalClaw 通道模块

支持多渠道集成：Telegram, Slack, Discord, WebSocket 等
"""

from fractalclaw.channels.base import (
    Channel,
    ChannelGroup,
    ChannelConfig,
    ChannelState,
    Message,
    MessageType,
    MessageHandler,
)

from fractalclaw.channels.telegram import TelegramChannel
from fractalclaw.channels.slack import SlackChannel
from fractalclaw.channels.discord import DiscordChannel

__all__ = [
    "Channel",
    "ChannelGroup",
    "ChannelConfig",
    "ChannelState",
    "Message",
    "MessageType",
    "MessageHandler",
    "TelegramChannel",
    "SlackChannel",
    "DiscordChannel",
]
