"""
FractalClaw 使用示例
"""

from fractalclaw import FractalAgent, AgentConfig
from fractalclaw.agent import Tool


def main():
    """主函数"""
    
    # 创建智能体配置
    config = AgentConfig(
        name="MyFractalAgent",
        model_provider="ollama",      # 使用本地 Ollama
        model_name="llama2",
        base_url="http://localhost:11434",
        enable_learning=True,
        enable_memory=True,
    )
    
    # 创建智能体
    agent = FractalAgent(config)
    
    # 初始化并启动
    agent.initialize()
    agent.start()
    
    # 注册自定义工具
    def hello_handler(name: str) -> str:
        return f"Hello, {name}!"
    
    agent.add_tool(Tool(
        name="hello",
        description="打招呼工具",
        handler=hello_handler
    ))
    
    # 运行智能体
    print("=== FractalClaw 智能体演示 ===\n")
    
    # 对话 1
    print("User: 帮我分析今天的工作任务")
    result = agent.run("帮我分析今天的工作任务")
    print(f"Agent: {result}\n")
    
    # 对话 2
    print("User: 搜索关于 Python 异步编程的信息")
    result = agent.run("搜索关于 Python 异步编程的信息")
    print(f"Agent: {result}\n")
    
    # 列出可用工具
    print("可用工具:", agent.list_tools())
    
    # 获取智能体状态
    print("\n=== 智能体内省 ===")
    info = agent.introspect()
    print(f"组件: {info['component_name']}")
    print(f"类型: {info['component_type']}")
    print(f"状态: {info['state']}")
    
    # 获取历史记录
    print("\n=== 历史记录 ===")
    history = agent.get_history()
    for h in history:
        print(f"- {h['timestamp']}: {h['prompt']} -> {h.get('status', 'unknown')}")
    
    # 触发进化
    print("\n=== 触发自我进化 ===")
    agent.evolve()
    
    # 停止智能体
    agent.stop()
    print("\n智能体已停止")


if __name__ == "__main__":
    main()
