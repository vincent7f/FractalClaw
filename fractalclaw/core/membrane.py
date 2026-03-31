"""
Membrane 控制膜 - 提供组件的非功能性服务

Fractal 通过 membrane 概念定制组件的非功能性服务
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging


class MembraneType(Enum):
    """控制膜类型"""
    LIFECYCLE = "lifecycle"         # 生命周期管理
    SECURITY = "security"           # 安全性
    TRANSACTION = "transaction"     # 事务管理
    CONCURRENCY = "concurrency"     # 并发控制
    LOGGING = "logging"             # 日志
    MONITORING = "monitoring"       # 监控
    CACHING = "caching"              # 缓存
    FAULT_TOLERANCE = "fault_tolerance"  # 容错


@dataclass
class MembraneConfig:
    """控制膜配置"""
    enabled: bool = True
    priority: int = 0
    config: Dict[str, Any] = field(default_factory=dict)


class MembraneContext:
    """控制膜上下文"""
    
    def __init__(self, component: 'Component'):
        self.component = component
        self.request_id: str = ""
        self.start_time: datetime = datetime.now()
        self.metadata: Dict[str, Any] = {}
    
    def set_metadata(self, key: str, value: Any):
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)


class Membrane(ABC):
    """
    控制膜 - 为组件提供非功能性服务
    
    类似于 AOP 的切面，可以在组件方法执行前后插入逻辑
    """
    
    def __init__(self, membrane_type: MembraneType, config: Optional[MembraneConfig] = None):
        self.membrane_type = membrane_type
        self.config = config or MembraneConfig()
        self._enabled = self.config.enabled
        self.logger = logging.getLogger(f"membrane.{membrane_type.value}")
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def before_invoke(self, context: MembraneContext, method: str, args: tuple, kwargs: dict) -> tuple:
        """方法调用前拦截"""
        if not self._enabled:
            return args, kwargs
        return self._on_before_invoke(context, method, args, kwargs)
    
    def after_invoke(self, context: MembraneContext, method: str, result: Any) -> Any:
        """方法调用后拦截"""
        if not self._enabled:
            return result
        return self._on_after_invoke(context, method, result)
    
    def on_error(self, context: MembraneContext, method: str, error: Exception) -> Exception:
        """错误处理"""
        if not self._enabled:
            return error
        return self._on_error(context, method, error)
    
    # ==================== 可覆盖的钩子方法 ====================
    
    def _on_before_invoke(self, context: MembraneContext, method: str, args: tuple, kwargs: dict) -> tuple:
        """调用前处理 - 子类可覆盖"""
        return args, kwargs
    
    def _on_after_invoke(self, context: MembraneContext, method: str, result: Any) -> Any:
        """调用后处理 - 子类可覆盖"""
        return result
    
    def _on_error(self, context: MembraneContext, method: str, error: Exception) -> Exception:
        """错误处理 - 子类可覆盖"""
        return error


class LifecycleMembrane(Membrane):
    """生命周期管理膜"""
    
    def __init__(self, config: Optional[MembraneConfig] = None):
        super().__init__(MembraneType.LIFECYCLE, config)
    
    def _on_before_invoke(self, context: MembraneContext, method: str, args: tuple, kwargs: dict) -> tuple:
        self.logger.debug(f"[{context.component.name}] Before {method}")
        return args, kwargs
    
    def _on_after_invoke(self, context: MembraneContext, method: str, result: Any) -> Any:
        self.logger.debug(f"[{context.component.name}] After {method}")
        return result


class SecurityMembrane(Membrane):
    """安全膜 - 权限检查"""
    
    def __init__(self, config: Optional[MembraneConfig] = None):
        super().__init__(MembraneType.SECURITY, config)
        self._policies: Dict[str, Callable] = {}
    
    def add_policy(self, method: str, policy: Callable):
        """添加安全策略"""
        self._policies[method] = policy
    
    def _on_before_invoke(self, context: MembraneContext, method: str, args: tuple, kwargs: dict) -> tuple:
        if method in self._policies:
            policy = self._policies[method]
            if not policy(context, args, kwargs):
                raise PermissionError(f"Security policy denied for method {method}")
        return args, kwargs


class TransactionMembrane(Membrane):
    """事务膜 - 支持事务操作"""
    
    def __init__(self, config: Optional[MembraneConfig] = None):
        super().__init__(MembraneType.TRANSACTION, config)
        self._transactions: Dict[str, Any] = {}
    
    def begin_transaction(self, transaction_id: str):
        self._transactions[transaction_id] = {"status": "active"}
    
    def commit_transaction(self, transaction_id: str):
        if transaction_id in self._transactions:
            self._transactions[transaction_id]["status"] = "committed"
    
    def rollback_transaction(self, transaction_id: str):
        if transaction_id in self._transactions:
            self._transactions[transaction_id]["status"] = "rolled_back"


class CachingMembrane(Membrane):
    """缓存膜"""
    
    def __init__(self, config: Optional[MembraneConfig] = None):
        super().__init__(MembraneType.CACHING, config)
        self._cache: Dict[str, Any] = {}
        self._ttl = config.config.get("ttl", 300) if config else 300
    
    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)
    
    def set(self, key: str, value: Any):
        self._cache[key] = value
    
    def clear(self):
        self._cache.clear()


class MembraneController:
    """控制膜控制器 - 管理组件的多个膜"""
    
    def __init__(self, component: 'Component'):
        self.component = component
        self._membranes: Dict[MembraneType, Membrane] = {}
    
    def add_membrane(self, membrane: Membrane):
        """添加控制膜"""
        self._membranes[membrane.membrane_type] = membrane
    
    def remove_membrane(self, membrane_type: MembraneType) -> Optional[Membrane]:
        """移除控制膜"""
        return self._membranes.pop(membrane_type, None)
    
    def get_membrane(self, membrane_type: MembraneType) -> Optional[Membrane]:
        """获取控制膜"""
        return self._membranes.get(membrane_type)
    
    def list_membranes(self) -> List[Membrane]:
        """列出所有控制膜"""
        return sorted(self._membranes.values(), key=lambda m: m.config.priority, reverse=True)
    
    def invoke_with_membranes(self, method: str, args: tuple, kwargs: dict) -> Any:
        """使用所有膜调用方法"""
        context = MembraneContext(self.component)
        
        # Before 阶段
        for membrane in self.list_membranes():
            args, kwargs = membrane.before_invoke(context, method, args, kwargs)
        
        # 执行方法
        result = None
        error = None
        try:
            if hasattr(self.component, method):
                result = getattr(self.component, method)(*args, **kwargs)
        except Exception as e:
            error = e
        
        # After 阶段
        if error:
            for membrane in reversed(self.list_membranes()):
                error = membrane.on_error(context, method, error)
            raise error
        else:
            for membrane in self.list_membranes():
                result = membrane.after_invoke(context, method, result)
        
        return result
