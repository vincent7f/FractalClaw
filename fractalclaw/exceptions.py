"""
FractalClaw 异常定义模块

提供统一的异常类体系，便于错误处理和调试。
"""

from typing import Any, Dict, Optional


class FractalClawException(Exception):
    """FractalClaw 基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"[{self.error_code}] {self.message} | Details: {self.details}"
        return f"[{self.error_code}] {self.message}"


class ConfigurationError(FractalClawException):
    """配置相关错误"""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, error_code="CONFIG_ERROR", details=details, **kwargs)


class ComponentError(FractalClawException):
    """组件相关错误"""

    def __init__(
        self,
        message: str,
        component_name: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if component_name:
            details["component_name"] = component_name
        super().__init__(message, error_code="COMPONENT_ERROR", details=details, **kwargs)


class ExecutionError(FractalClawException):
    """执行相关错误"""

    def __init__(
        self,
        message: str,
        task_id: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if task_id:
            details["task_id"] = task_id
        super().__init__(message, error_code="EXECUTION_ERROR", details=details, **kwargs)


class MemoryError(FractalClawException):
    """记忆存储相关错误"""

    def __init__(
        self,
        message: str,
        memory_id: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if memory_id:
            details["memory_id"] = memory_id
        super().__init__(message, error_code="MEMORY_ERROR", details=details, **kwargs)


class ToolError(FractalClawException):
    """工具相关错误"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if tool_name:
            details["tool_name"] = tool_name
        super().__init__(message, error_code="TOOL_ERROR", details=details, **kwargs)


class BindingError(FractalClawException):
    """绑定相关错误"""

    def __init__(
        self,
        message: str,
        binding_name: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if binding_name:
            details["binding_name"] = binding_name
        super().__init__(message, error_code="BINDING_ERROR", details=details, **kwargs)


class LLMError(FractalClawException):
    """LLM API 调用相关错误"""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if provider:
            details["provider"] = provider
        if model:
            details["model"] = model
        super().__init__(message, error_code="LLM_ERROR", details=details, **kwargs)
