"""
FractalClaw - 基于Fractal架构的可进化智能体框架

参考 https://fractal.ow2.io/ 的组件模型设计
实现类似 OpenClaw (https://openclaw.im/) 的 AI 助手功能
"""

from .core.component import Component, CompositeComponent, LeafComponent
from .core.binding import Binding, BindingManager
from .core.membrane import Membrane, MembraneController
from .core.introspection import Introspection, Introspectable
from .agent.fractal_agent import FractalAgent, AgentConfig
from .agent.capability import Capability, CapabilityRegistry
from .agent.memory import MemoryComponent, MemoryStore
from .agent.planner import PlannerComponent, Task
from .agent.executor import ExecutorComponent, Tool
from .agent.learning import LearningComponent, EvolutionEngine
from .agent.message_router import MessageRouterComponent, Platform
from .agent.plugin import Plugin, PluginManager
from .history import (
    HistoryRecorder,
    get_recorder,
    record_conversation,
    record_user_message,
    record_assistant_message,
    record_system_message,
    read_conversation_history,
)

__version__ = "0.1.0"

__all__ = [
    # Core
    "Component",
    "CompositeComponent", 
    "LeafComponent",
    "Binding",
    "BindingManager",
    "Membrane",
    "MembraneController",
    "Introspection",
    "Introspectable",
    # Agent
    "FractalAgent",
    "AgentConfig",
    # Memory
    "Capability",
    "CapabilityRegistry",
    "MemoryComponent",
    "MemoryStore",
    "MemoryItem",
    # Planner
    "PlannerComponent",
    "Task",
    "Plan",
    "TaskStatus",
    "TaskPriority",
    # Executor
    "ExecutorComponent",
    "Tool",
    "ToolType",
    # Learning
    "LearningComponent",
    "EvolutionEngine",
    # Message Router
    "MessageRouterComponent",
    "Platform",
    "Message",
    # Plugin
    "Plugin",
    "PluginManager",
    "PluginMetadata",
    # History
    "HistoryRecorder",
    "get_recorder",
    "record_conversation",
    "record_user_message",
    "record_assistant_message",
    "record_system_message",
    "read_conversation_history",
]
