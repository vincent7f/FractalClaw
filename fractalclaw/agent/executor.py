"""
Executor 组件 - 执行组件

负责执行任务和工具调用
"""

# 标准库
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# 本地模块
from ..core.component import Component, ClientInterface, ServiceInterface
from ..exceptions import ExecutionError, ToolError
from ..logger import executor_logger
from .planner import Plan, Task, TaskStatus


class ToolType(Enum):
    """工具类型"""
    FUNCTION = "function"
    SEARCH = "search"
    COMPUTE = "compute"
    FILE = "file"
    SHELL = "shell"
    API = "api"
    CUSTOM = "custom"


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    type: ToolType = ToolType.FUNCTION
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None
    enabled: bool = True

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """执行工具"""
        if not self.enabled:
            raise ToolError(
                message=f"Tool {self.name} is disabled",
                tool_name=self.name,
            )

        if self.handler:
            try:
                return self.handler(*args, **kwargs)
            except Exception as e:
                executor_logger.error(f"Tool {self.name} execution failed: {e}")
                raise ToolError(
                    message=f"Tool execution failed: {str(e)}",
                    tool_name=self.name,
                ) from e

        raise NotImplementedError(f"Tool {self.name} has no handler")

    async def execute_async(self, *args: Any, **kwargs: Any) -> Any:
        """异步执行工具"""
        if not self.enabled:
            raise ToolError(
                message=f"Tool {self.name} is disabled",
                tool_name=self.name,
            )

        if self.handler:
            if asyncio.iscoroutinefunction(self.handler):
                try:
                    return await self.handler(*args, **kwargs)
                except Exception as e:
                    executor_logger.error(f"Tool {self.name} async execution failed: {e}")
                    raise ToolError(
                        message=f"Tool async execution failed: {str(e)}",
                        tool_name=self.name,
                    ) from e
            return self.execute(*args, **kwargs)
        raise NotImplementedError(f"Tool {self.name} has no handler")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "parameters": self.parameters,
            "enabled": self.enabled,
        }


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration": self.duration,
            "metadata": self.metadata,
        }


class ExecutorComponent(Component):
    """
    执行组件 - 负责执行任务和工具调用

    支持:
    - 同步/异步执行
    - 工具管理
    - 执行上下文
    - 错误处理
    """

    def __init__(self, name: str):
        super().__init__(name)
        self._tools: Dict[str, Tool] = {}
        self._execution_history: List[ExecutionResult] = []

        # 注册内置工具
        self._register_builtin_tools()

        # 定义接口
        self.add_interface(
            ServiceInterface(
                "executor_interface",
                ["execute", "execute_async", "register_tool", "list_tools"],
            )
        )
        self.add_interface(ClientInterface("client_interface", []))

    def _register_builtin_tools(self) -> None:
        """注册内置工具"""
        # 搜索工具
        self.register_tool(
            Tool(
                name="search",
                description="搜索信息",
                type=ToolType.SEARCH,
                handler=self._search_handler,
            )
        )

        # 计算工具
        self.register_tool(
            Tool(
                name="compute",
                description="执行计算",
                type=ToolType.COMPUTE,
                handler=self._compute_handler,
            )
        )

        # 当前时间工具
        self.register_tool(
            Tool(
                name="current_time",
                description="获取当前时间",
                type=ToolType.FUNCTION,
                handler=self._current_time_handler,
            )
        )

    def _search_handler(self, query: str) -> str:
        """搜索处理器"""
        return f"搜索结果 for: {query}"

    def _compute_handler(self, expression: str) -> Any:
        """计算处理器"""
        try:
            return eval(expression)
        except Exception as e:
            executor_logger.warning(f"Compute error: {e}")
            return f"Error: {str(e)}"

    def _current_time_handler(self) -> str:
        """当前时间处理器"""
        return datetime.now().isoformat()

    def register_tool(self, tool: Tool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        executor_logger.info(f"Tool registered: {tool.name}")

    def unregister_tool(self, name: str) -> Optional[Tool]:
        """注销工具"""
        tool = self._tools.pop(name, None)
        if tool:
            executor_logger.info(f"Tool unregistered: {name}")
        return tool

    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """列出所有工具"""
        return list(self._tools.keys())

    def list_tools_detail(self) -> List[Dict[str, Any]]:
        """列出所有工具详情"""
        return [tool.to_dict() for tool in self._tools.values()]

    def execute(
        self,
        plan: Plan,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行计划

        Args:
            plan: 计划对象
            context: 执行上下文

        Returns:
            执行结果
        """
        executor_logger.info(f"Executing plan: {plan.id}")
        results = []
        context = context or {}

        for task in plan.tasks:
            result = self._execute_task(task, context)
            results.append(result.to_dict())

            if not result.success:
                executor_logger.warning(f"Task {task.name} failed: {result.error}")
                break

        success = all(r["success"] for r in results)
        executor_logger.info(f"Plan {plan.id} execution completed: success={success}")

        return {
            "plan_id": plan.id,
            "goal": plan.goal,
            "results": results,
            "success": success,
        }

    def _execute_task(self, task: Task, context: Dict[str, Any]) -> ExecutionResult:
        """执行单个任务"""
        start_time = datetime.now()

        try:
            # 根据任务名称匹配工具
            tool = self._tools.get(task.name)

            if tool:
                output = tool.execute(context.get("query", ""))
            else:
                # 默认处理
                output = f"Task '{task.name}' processed with context: {context}"

            duration = (datetime.now() - start_time).total_seconds()

            return ExecutionResult(
                success=True,
                output=output,
                duration=duration,
                metadata={"task_id": task.id},
            )

        except ToolError:
            raise
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            executor_logger.error(f"Task {task.name} execution error: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                duration=duration,
                metadata={"task_id": task.id},
            )

    async def execute_async(
        self,
        plan: Plan,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """异步执行计划"""
        executor_logger.info(f"Executing plan async: {plan.id}")
        results = []
        context = context or {}

        for task in plan.tasks:
            result = await self._execute_task_async(task, context)
            results.append(result.to_dict())

            if not result.success:
                break

        success = all(r["success"] for r in results)
        return {
            "plan_id": plan.id,
            "goal": plan.goal,
            "results": results,
            "success": success,
        }

    async def _execute_task_async(
        self,
        task: Task,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """异步执行任务"""
        start_time = datetime.now()

        try:
            tool = self._tools.get(task.name)

            if tool:
                output = await tool.execute_async(context.get("query", ""))
            else:
                output = f"Task '{task.name}' processed"

            duration = (datetime.now() - start_time).total_seconds()

            return ExecutionResult(
                success=True,
                output=output,
                duration=duration,
                metadata={"task_id": task.id},
            )

        except ToolError:
            raise
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            executor_logger.error(f"Async task {task.name} execution error: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                duration=duration,
                metadata={"task_id": task.id},
            )

    def execute_tool(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        """直接执行工具"""
        tool = self._tools.get(tool_name)
        if not tool:
            raise ToolError(
                message=f"Tool {tool_name} not found",
                tool_name=tool_name,
            )
        return tool.execute(*args, **kwargs)

    def _on_initialize(self) -> None:
        pass

    def _on_start(self) -> None:
        pass

    def _on_stop(self) -> None:
        pass
