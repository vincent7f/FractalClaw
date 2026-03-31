# FractalClaw - 基于Fractal架构的可进化智能体

## 概述

FractalClaw 是一个参考 Fractal 组件模型设计的可进化智能体框架，结合了 OpenClaw 的核心功能特性。

## 核心特性

### 1. Fractal 架构特性
- **递归组件结构**: 组件可以嵌套形成层次化结构
- **反射能力**: 组件具备内省和干预能力
- **动态绑定**: 组件间使用灵活的绑定机制
- **执行模型独立性**: 支持多种执行模型

### 2. OpenClaw 风格功能
- **多平台消息路由**: 支持多种消息平台
- **持久化记忆**: 记住用户偏好和上下文
- **工作流自动化**: 可编程的 AI 工作流
- **插件系统**: 可扩展的插件架构
- **自带模型 (BYOM)**: 支持多种 LLM 提供商

### 3. 自我进化能力
- **能力学习**: 从交互中学习新技能
- **结构演化**: 动态调整组件结构
- **自适应优化**: 根据任务自动优化

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

```python
from fractalclaw import FractalAgent, AgentConfig

# 创建配置
config = AgentConfig(
    name="MyFractalAgent",
    model_provider="ollama",
    model_name="llama2",
    base_url="http://localhost:11434",
)

# 创建智能体
agent = FractalAgent(config)

# 初始化并启动
agent.initialize()
agent.start()

# 运行智能体
result = agent.run("帮我分析今天的工作任务")
print(result)

# 触发自我进化
agent.evolve()

# 停止智能体
agent.stop()
```

## API 参考

### AgentConfig

智能体配置类。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | "FractalAgent" | 智能体名称 |
| `model_provider` | `str` | "openai" | 模型提供商 (openai/anthropic/ollama) |
| `model_name` | `str` | "gpt-4" | 模型名称 |
| `api_key` | `Optional[str]` | None | API 密钥 |
| `base_url` | `Optional[str]` | None | API 基础 URL |
| `max_iterations` | `int` | 100 | 最大迭代次数 |
| `timeout` | `int` | 300 | 超时时间(秒) |
| `enable_learning` | `bool` | True | 启用学习功能 |
| `enable_memory` | `bool` | True | 启用记忆功能 |
| `log_level` | `str` | "INFO" | 日志级别 |

### FractalAgent

主智能体类。

#### 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `initialize()` | `None` | 初始化智能体 |
| `start()` | `None` | 启动智能体 |
| `stop()` | `None` | 停止智能体 |
| `run(prompt, context)` | `Dict[str, Any]` | 运行智能体 |
| `run_async(prompt, context)` | `Dict[str, Any]` | 异步运行智能体 |
| `chat(message)` | `str` | 简单聊天接口 |
| `introspect()` | `Dict[str, Any]` | 获取智能体状态 |
| `get_history()` | `List[Dict]` | 获取历史记录 |
| `clear_history()` | `None` | 清空历史记录 |
| `add_tool(tool)` | `None` | 添加工具 |
| `list_tools()` | `List[str]` | 列出可用工具 |
| `evolve()` | `None` | 触发自我进化 |

### 异常类

| 异常类 | 说明 |
|--------|------|
| `FractalClawException` | 基础异常类 |
| `ConfigurationError` | 配置相关错误 |
| `ComponentError` | 组件相关错误 |
| `ExecutionError` | 执行相关错误 |
| `MemoryError` | 记忆存储相关错误 |
| `ToolError` | 工具相关错误 |
| `LLMError` | LLM API 调用相关错误 |

## 架构

```
FractalAgent (复合组件)
├── MemoryComponent (记忆组件)
├── PlannerComponent (规划组件)
├── ExecutorComponent (执行组件)
├── LearningComponent (学习组件)
├── ToolRegistryComponent (工具注册组件)
└── MessageRouterComponent (消息路由组件)
```

## 核心模块

### 核心组件 (fractalclaw/core)
- **component.py**: Component, CompositeComponent, LeafComponent
- **binding.py**: Binding, BindingManager - 组件间连接
- **membrane.py**: Membrane, MembraneController - 非功能性服务
- **introspection.py**: Introspection - 内省能力

### 智能体组件 (fractalclaw/agent)
- **fractal_agent.py**: FractalAgent - 主智能体类
- **memory.py**: MemoryComponent - 持久化记忆
- **planner.py**: PlannerComponent - 任务规划
- **executor.py**: ExecutorComponent - 任务执行
- **learning.py**: LearningComponent - 自我进化
- **tool_registry.py**: ToolRegistryComponent - 工具管理
- **message_router.py**: MessageRouterComponent - 消息路由
- **plugin.py**: Plugin, PluginManager - 插件系统
- **capability.py**: Capability, CapabilityRegistry - 能力系统

### 客户端 (fractalclaw/clients)
- **ollama.py**: OllamaClient - Ollama API 客户端

### 工具模块
- **exceptions.py**: 统一异常类
- **logger.py**: 日志模块

## 对话历史

所有对话都会自动记录到 `docs/prompts/histories.log` 文件中，包含时间戳。

## 参考

- [Fractal Architecture](https://fractal.ow2.io/)
- [OpenClaw](https://openclaw.im/)

## License

MIT
