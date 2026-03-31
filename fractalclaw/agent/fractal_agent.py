"""
FractalAgent - 基于Fractal架构的可进化智能体

结合 OpenClaw 功能特性实现
"""

# 标准库
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# 第三方库
from openai import AsyncOpenAI

# 本地模块
from ..clients import OllamaClient
from ..core.binding import Binding, BindingType, BindingManager
from ..core.component import CompositeComponent, ComponentMetadata, ComponentState
from ..core.introspection import Introspection, Introspectable
from ..core.membrane import LifecycleMembrane, MembraneController
from ..exceptions import ConfigurationError, LLMError
from ..logger import agent_logger


@dataclass
class AgentConfig:
    """智能体配置"""
    name: str = "FractalAgent"
    model_provider: str = "openai"  # openai, anthropic, ollama
    model_name: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_iterations: int = 100
    timeout: int = 300
    enable_learning: bool = True
    enable_memory: bool = True
    enable_tools: bool = True
    log_level: str = "INFO"


class FractalAgent(CompositeComponent, Introspectable):
    """
    Fractal 智能体 - 可进化的 AI 智能体

    核心组件:
    - MemoryComponent: 记忆组件
    - PlannerComponent: 规划组件
    - ExecutorComponent: 执行组件
    - LearningComponent: 学习组件
    - ToolRegistryComponent: 工具注册组件
    - MessageRouterComponent: 消息路由组件
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()

        metadata = ComponentMetadata(
            name=self.config.name,
            description="基于Fractal架构的可进化智能体"
        )
        super().__init__(self.config.name, metadata)

        self._config = self.config
        self._binding_manager = BindingManager()
        self._membrane_controller = MembraneController(self)
        self._running = False
        self._history: List[Dict[str, Any]] = []
        self._llm_client: Optional[AsyncOpenAI | OllamaClient] = None

        # 添加生命周期膜
        self._membrane_controller.add_membrane(LifecycleMembrane())

        # 初始化子组件
        self._init_components()

    def _init_components(self) -> None:
        """初始化组件"""
        from ..agent.memory import MemoryComponent, MemoryStore
        from ..agent.planner import PlannerComponent
        from ..agent.executor import ExecutorComponent
        from ..agent.learning import LearningComponent
        from ..agent.tool_registry import ToolRegistryComponent
        from ..agent.message_router import MessageRouterComponent

        # 记忆组件
        memory_store = MemoryStore()
        self.memory = MemoryComponent("memory", memory_store)
        self.add_child(self.memory)

        # 规划组件
        self.planner = PlannerComponent("planner")
        self.add_child(self.planner)

        # 执行组件
        self.executor = ExecutorComponent("executor")
        self.add_child(self.executor)

        # 学习组件
        if self.config.enable_learning:
            self.learning = LearningComponent("learning")
            self.add_child(self.learning)

        # 工具注册组件
        self.tool_registry = ToolRegistryComponent("tool_registry")
        self.add_child(self.tool_registry)

        # 消息路由组件
        self.message_router = MessageRouterComponent("message_router")
        self.add_child(self.message_router)

        # 建立组件间绑定
        self._setup_bindings()

    def _setup_bindings(self) -> None:
        """建立组件间绑定"""
        # Memory -> Planner
        binding = Binding(
            "memory_to_planner",
            self.memory, "memory_interface",
            self.planner, "planner_interface",
            BindingType.SYNC
        )
        self._binding_manager.add_binding(binding)

        # Planner -> Executor
        binding = Binding(
            "planner_to_executor",
            self.planner, "planner_interface",
            self.executor, "executor_interface",
            BindingType.SYNC
        )
        self._binding_manager.add_binding(binding)

        # Executor -> Memory (反馈)
        binding = Binding(
            "executor_to_memory",
            self.executor, "executor_interface",
            self.memory, "memory_interface",
            BindingType.SYNC
        )
        self._binding_manager.add_binding(binding)

        # Learning -> Memory
        if hasattr(self, 'learning'):
            binding = Binding(
                "learning_to_memory",
                self.learning, "learning_interface",
                self.memory, "memory_interface",
                BindingType.SYNC
            )
            self._binding_manager.add_binding(binding)

    def initialize(self) -> None:
        """初始化智能体"""
        super().initialize()
        agent_logger.info(f"Initializing agent: {self.config.name}")

        # 初始化 LLM 客户端
        self._init_llm_client()

    def _init_llm_client(self) -> None:
        """初始化 LLM 客户端"""
        try:
            if self._config.model_provider == "openai":
                self._llm_client = AsyncOpenAI(
                    api_key=self._config.api_key,
                    base_url=self._config.base_url
                )
                agent_logger.info("OpenAI client initialized")

            elif self._config.model_provider == "anthropic":
                try:
                    import anthropic
                    self._llm_client = anthropic.AsyncAnthropic(
                        api_key=self._config.api_key
                    )
                    agent_logger.info("Anthropic client initialized")
                except ImportError:
                    agent_logger.warning("anthropic package not installed")
                    self._llm_client = None

            elif self._config.model_provider == "ollama":
                self._llm_client = OllamaClient(
                    base_url=self._config.base_url or "http://localhost:11434"
                )
                agent_logger.info("Ollama client initialized")

            else:
                raise ConfigurationError(
                    message=f"Unsupported model provider: {self._config.model_provider}",
                    config_key="model_provider",
                )

        except ConfigurationError:
            raise
        except Exception as e:
            agent_logger.error(f"Failed to initialize LLM client: {e}")
            raise LLMError(
                message=f"Failed to initialize LLM client: {str(e)}",
                provider=self._config.model_provider,
                model=self._config.model_name,
            ) from e

    def run(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        运行智能体

        Args:
            prompt: 用户输入
            context: 额外上下文

        Returns:
            运行结果
        """
        if self.state != ComponentState.STARTED:
            self.initialize()
            self.start()

        start_time = datetime.now()
        agent_logger.info(f"Running agent with prompt: {prompt[:50]}...")

        # 记录历史
        record: Dict[str, Any] = {
            "timestamp": start_time.isoformat(),
            "prompt": prompt,
            "context": context,
        }

        try:
            # 1. 记忆检索
            relevant_memories = self.memory.retrieve(prompt)

            # 2. 规划
            plan = self.planner.create_plan(prompt, relevant_memories)

            # 3. 执行
            result = self.executor.execute(plan, context)

            # 4. 学习 (如果启用)
            if hasattr(self, 'learning') and self._config.enable_learning:
                self.learning.learn(prompt, result)

            # 5. 记忆存储
            self.memory.store(prompt, result)

            record["result"] = result
            record["status"] = "success"
            agent_logger.info(f"Agent run completed successfully in {(datetime.now() - start_time).total_seconds():.2f}s")

        except Exception as e:
            record["error"] = str(e)
            record["status"] = "failed"
            result = {"error": str(e)}
            agent_logger.error(f"Agent run failed: {e}", exc_info=True)

        record["duration"] = (datetime.now() - start_time).total_seconds()
        self._history.append(record)

        return result

    async def run_async(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """异步运行智能体"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run, prompt, context)

    def chat(self, message: str) -> str:
        """简单的聊天接口"""
        result = self.run(message)
        return result.get("response", result.get("error", "No response"))

    def introspect(self) -> Dict[str, Any]:
        """内省智能体"""
        return Introspection(self).inspect().to_dict()

    def get_history(self) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return self._history.copy()

    def clear_history(self) -> None:
        """清空历史记录"""
        self._history.clear()
        agent_logger.info("History cleared")

    def add_tool(self, tool: 'Tool') -> None:
        """添加工具"""
        self.tool_registry.register_tool(tool)
        agent_logger.info(f"Tool registered: {tool.name}")

    def list_tools(self) -> List[str]:
        """列出可用工具"""
        return self.tool_registry.list_tools()

    def evolve(self) -> None:
        """触发自我进化"""
        if hasattr(self, 'learning'):
            self.learning.evolve()
            agent_logger.info("Agent evolution triggered")

    def __repr__(self) -> str:
        return f"FractalAgent(name={self.config.name}, state={self.state.value})"


# Tool 类型需要从 executor 模块导入，放在文件末尾避免循环导入
from ..agent.executor import Tool
