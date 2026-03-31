"""
测试本地 Ollama gemma3:12b 模型
"""

import asyncio
import aiohttp
from fractalclaw.clients import OllamaClient


async def list_models_async(client: OllamaClient):
    """异步获取模型列表"""
    url = f"{client.base_url}/api/tags"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to list models: {resp.status}")
            data = await resp.json()
            return data.get("models", [])


async def test_ollama():
    """测试 Ollama 客户端"""
    client = OllamaClient(base_url="http://localhost:11434")
    
    # 1. 列出可用模型
    print("=" * 50)
    print("1. 获取可用模型列表:")
    print("=" * 50)
    try:
        models = await list_models_async(client)
        for model in models:
            print(f"  - {model.get('name', 'unknown')}")
    except Exception as e:
        print(f"  获取模型列表失败: {e}")
    
    # 2. 测试 chat 功能
    print("\n" + "=" * 50)
    print("2. 测试 chat 功能 (gemma3:12b):")
    print("=" * 50)
    
    messages = [
        {"role": "system", "content": "你是一个有用的AI助手。请用简洁的语言回答。"},
        {"role": "user", "content": "你好！请介绍一下你自己。"}
    ]
    
    try:
        response = await client.chat(
            model="gemma3:12b",
            messages=messages,
            stream=False
        )
        print(f"\n模型: gemma3:12b")
        print(f"回复: {response.get('message', {}).get('content', 'No content')}")
        print(f"完整响应: {response}")
    except Exception as e:
        print(f"  Chat 测试失败: {e}")
    
    # 3. 测试 generate 功能
    print("\n" + "=" * 50)
    print("3. 测试 generate 功能 (gemma3:12b):")
    print("=" * 50)
    
    try:
        response = await client.generate(
            model="gemma3:12b",
            prompt="用一句话介绍Python编程语言",
            stream=False
        )
        print(f"\n模型: gemma3:12b")
        print(f"回复: {response.get('response', 'No content')}")
    except Exception as e:
        print(f"  Generate 测试失败: {e}")


if __name__ == "__main__":
    print("开始测试本地 Ollama gemma3:12b 模型...")
    print()
    asyncio.run(test_ollama())
    print("\n测试完成!")
