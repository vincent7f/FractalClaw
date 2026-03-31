"""
Ollama 客户端实现

提供对 Ollama API 的异步访问。
"""

from typing import Any, Dict, List, Optional

import aiohttp

from ..exceptions import LLMError
from ..logger import get_logger

logger = get_logger("ollama")


class OllamaClient:
    """Ollama 客户端"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: int = 300,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        发送聊天请求

        Args:
            model: 模型名称
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            API 响应

        Raises:
            LLMError: API 调用失败
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            **kwargs,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Ollama API error: {resp.status} - {error_text}")
                        raise LLMError(
                            message=f"Ollama API returned status {resp.status}",
                            provider="ollama",
                            model=model,
                            details={"status": resp.status, "error": error_text},
                        )
                    return await resp.json()

        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise LLMError(
                message=f"Failed to connect to Ollama: {str(e)}",
                provider="ollama",
                model=model,
            ) from e

        except LLMError:
            raise

        except Exception as e:
            logger.error(f"Unexpected error calling Ollama: {e}")
            raise LLMError(
                message=f"Unexpected error: {str(e)}",
                provider="ollama",
                model=model,
            ) from e

    async def generate(
        self,
        model: str,
        prompt: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        生成文本

        Args:
            model: 模型名称
            prompt: 提示词
            **kwargs: 其他参数

        Returns:
            API 响应
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            **kwargs,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise LLMError(
                            message=f"Ollama API returned status {resp.status}",
                            provider="ollama",
                            model=model,
                        )
                    return await resp.json()

        except aiohttp.ClientError as e:
            raise LLMError(
                message=f"Failed to connect to Ollama: {str(e)}",
                provider="ollama",
                model=model,
            ) from e

    def list_models(self) -> List[Dict[str, Any]]:
        """
        获取可用模型列表

        Returns:
            模型列表
        """
        url = f"{self.base_url}/api/tags"

        import asyncio

        async def _list():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise LLMError(
                            message=f"Failed to list models: {resp.status}",
                            provider="ollama",
                        )
                    data = await resp.json()
                    return data.get("models", [])

        return asyncio.run(_list())
