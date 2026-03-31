"""
语音处理模块

提供语音识别 (STT) 和语音合成 (TTS) 功能
"""

from typing import Dict, List, Any, Optional, Callable, Awaitable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
import base64
import json

from fractalclaw.core.component import Component, LeafComponent, ComponentState


class VoiceProvider(Enum):
    """语音服务提供商"""
    OPENAI = "openai"
    GOOGLE = "google"
    AZURE = "azure"
    ELEVENLABS = "elevenlabs"
    COQUI = "coqui"


@dataclass
class AudioConfig:
    """音频配置"""
    sample_rate: int = 16000
    channels: int = 1
    format: str = "wav"
    codec: str = "pcm"


@dataclass
class TranscriptionResult:
    """转录结果"""
    text: str = ""
    language: Optional[str] = None
    confidence: float = 0.0
    duration: float = 0.0
    segments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SynthesisResult:
    """合成结果"""
    audio_data: Optional[bytes] = None
    audio_url: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# 音频处理器类型
AudioHandler = Callable[[bytes], Awaitable[None]]


class STTProvider(ABC):
    """语音识别提供商基类"""

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """转录音频"""
        pass

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """流式转录"""
        pass


class TTSProvider(ABC):
    """语音合成提供商基类"""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        language: str = "en",
    ) -> SynthesisResult:
        """合成语音"""
        pass


class VoiceManager(LeafComponent):
    """
    语音管理器
    
    提供统一的语音识别和语音合成接口
    """

    def __init__(
        self,
        name: str = "voice",
        config: Optional[AudioConfig] = None,
    ):
        super().__init__(name)
        self.config = config or AudioConfig()
        
        self._stt_providers: Dict[VoiceProvider, STTProvider] = {}
        self._tts_providers: Dict[VoiceProvider, TTSProvider] = {}
        self._active_stt: Optional[VoiceProvider] = None
        self._active_tts: Optional[VoiceProvider] = None
        self._audio_handlers: Dict[str, AudioHandler] = {}

    # ==================== 提供商注册 ====================

    def register_stt_provider(
        self,
        provider: VoiceProvider,
        stt: STTProvider,
    ):
        """注册语音识别提供商"""
        self._stt_providers[provider] = stt
        if self._active_stt is None:
            self._active_stt = provider

    def register_tts_provider(
        self,
        provider: VoiceProvider,
        tts: TTSProvider,
    ):
        """注册语音合成提供商"""
        self._tts_providers[provider] = tts
        if self._active_tts is None:
            self._active_tts = provider

    def set_active_stt(self, provider: VoiceProvider) -> bool:
        """设置活跃的语音识别提供商"""
        if provider in self._stt_providers:
            self._active_stt = provider
            return True
        return False

    def set_active_tts(self, provider: VoiceProvider) -> bool:
        """设置活跃的语音合成提供商"""
        if provider in self._tts_providers:
            self._active_tts = provider
            return True
        return False

    # ==================== 语音识别 ====================

    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """转录音频"""
        if self._active_stt is None:
            return TranscriptionResult(text="No STT provider available")
        
        provider = self._stt_providers.get(self._active_stt)
        if provider:
            return await provider.transcribe(audio_data, language)
        
        return TranscriptionResult(text="STT provider not configured")

    async def transcribe_base64(
        self,
        audio_base64: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """转录 Base64 编码的音频"""
        try:
            audio_data = base64.b64decode(audio_base64)
            return await self.transcribe(audio_data, language)
        except Exception as e:
            return TranscriptionResult(text=f"Error: {str(e)}")

    async def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """转录音频文件"""
        try:
            with open(file_path, "rb") as f:
                audio_data = f.read()
            return await self.transcribe(audio_data, language)
        except Exception as e:
            return TranscriptionResult(text=f"Error: {str(e)}")

    async def transcribe_stream(
        self,
        audio_stream: Any,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """流式转录"""
        if self._active_stt is None:
            return TranscriptionResult(text="No STT provider available")
        
        provider = self._stt_providers.get(self._active_stt)
        if provider:
            return await provider.transcribe_stream(audio_stream, language)
        
        return TranscriptionResult(text="STT provider not configured")

    # ==================== 语音合成 ====================

    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        language: str = "en",
    ) -> SynthesisResult:
        """合成语音"""
        if self._active_tts is None:
            return SynthesisResult()
        
        provider = self._tts_providers.get(self._active_tts)
        if provider:
            return await provider.synthesize(text, voice, language)
        
        return SynthesisResult()

    async def synthesize_to_file(
        self,
        text: str,
        file_path: str,
        voice: str = "default",
        language: str = "en",
    ) -> bool:
        """合成语音并保存到文件"""
        result = await self.synthesize(text, voice, language)
        
        if result.audio_data:
            with open(file_path, "wb") as f:
                f.write(result.audio_data)
            return True
        
        return False

    async def synthesize_to_base64(
        self,
        text: str,
        voice: str = "default",
        language: str = "en",
    ) -> Optional[str]:
        """合成语音并返回 Base64"""
        result = await self.synthesize(text, voice, language)
        
        if result.audio_data:
            return base64.b64encode(result.audio_data).decode()
        
        return None

    # ==================== 实时语音 ====================

    def register_audio_handler(
        self,
        stream_id: str,
        handler: AudioHandler,
    ):
        """注册音频处理器"""
        self._audio_handlers[stream_id] = handler

    def unregister_audio_handler(self, stream_id: str):
        """注销音频处理器"""
        self._audio_handlers.pop(stream_id, None)

    async def process_audio(
        self,
        stream_id: str,
        audio_data: bytes,
    ):
        """处理音频数据"""
        handler = self._audio_handlers.get(stream_id)
        if handler:
            await handler(audio_data)


# ==================== 实现示例 ====================

class OpenAITTS(TTSProvider):
    """OpenAI TTS 实现"""

    def __init__(self, api_key: str, model: str = "tts-1"):
        self.api_key = api_key
        self.model = model
        self.api_base = "https://api.openai.com/v1"

    async def synthesize(
        self,
        text: str,
        voice: str = "alloy",
        language: str = "en",
    ) -> SynthesisResult:
        """使用 OpenAI TTS 合成语音"""
        import aiohttp
        
        url = f"{self.api_base}/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "voice": voice,
            "input": text,
            "response_format": "wav",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        return SynthesisResult(audio_data=audio_data)
        except Exception as e:
            pass
        
        return SynthesisResult()


class OpenAISTT(STTProvider):
    """OpenAI STT 实现 (Whisper)"""

    def __init__(self, api_key: str, model: str = "whisper-1"):
        self.api_key = api_key
        self.model = model
        self.api_base = "https://api.openai.com/v1"

    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """使用 OpenAI Whisper 转录音频"""
        import aiohttp
        
        url = f"{self.api_base}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        
        form = aiohttp.FormData()
        form.add_field("file", audio_data, filename="audio.wav", content_type="audio/wav")
        form.add_field("model", self.model)
        
        if language:
            form.add_field("language", language)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=form, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        return TranscriptionResult(
                            text=result.get("text", ""),
                            language=language,
                        )
        except Exception as e:
            pass
        
        return TranscriptionResult(text="Transcription failed")

    async def transcribe_stream(
        self,
        audio_stream: Any,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """流式转录（简化实现）"""
        # 收集所有音频数据后转录
        chunks = []
        async for chunk in audio_stream:
            chunks.append(chunk)
        
        audio_data = b"".join(chunks)
        return await self.transcribe(audio_data, language)
