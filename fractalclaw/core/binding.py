"""
Binding 组件 - 组件间连接机制

Fractal 使用单一的绑定抽象来处理组件间的连接
"""

from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import asyncio


class BindingType(Enum):
    """绑定类型"""
    SYNC = "sync"              # 同步方法调用
    ASYNC = "async"            # 异步方法调用
    RPC = "rpc"                # 远程过程调用
    EVENT = "event"            # 事件驱动
    STREAM = "stream"          # 流式数据


@dataclass
class BindingContext:
    """绑定上下文"""
    source_component: Any
    source_interface: str
    target_component: Any
    target_interface: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Binding:
    """
    绑定 - 连接组件接口的实体
    
    可以嵌入任何通信语义
    """
    
    def __init__(
        self,
        name: str,
        source: Any,
        source_interface: str,
        target: Any,
        target_interface: str,
        binding_type: BindingType = BindingType.SYNC,
        transform: Optional[Callable] = None,
        middleware: Optional[list] = None
    ):
        self.name = name
        self.source = source
        self.source_interface = source_interface
        self.target = target
        self.target_interface = target_interface
        self.binding_type = binding_type
        self.transform = transform or (lambda x: x)
        self.middleware = middleware or []
        self._enabled = True
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    def invoke(self, method: str, *args, **kwargs) -> Any:
        """调用绑定的方法"""
        if not self._enabled:
            raise RuntimeError(f"Binding {self.name} is disabled")
        
        # 应用中间件
        for mw in self.middleware:
            args, kwargs = mw(args, kwargs) or (args, kwargs)
        
        # 转换输入
        args = (self.transform(args),) if args else ()
        
        # 调用目标方法
        if hasattr(self.target, method):
            return getattr(self.target, method)(*args, **kwargs)
        raise AttributeError(f"Target has no method {method}")
    
    async def invoke_async(self, method: str, *args, **kwargs) -> Any:
        """异步调用"""
        if not self._enabled:
            raise RuntimeError(f"Binding {self.name} is disabled")
        
        # 应用中间件
        for mw in self.middleware:
            args, kwargs = mw(args, kwargs) or (args, kwargs)
        
        # 转换输入
        args = (self.transform(args),) if args else ()
        
        # 调用目标方法
        if asyncio.iscoroutinefunction(getattr(self.target, method, None)):
            return await getattr(self.target, method)(*args, **kwargs)
        return getattr(self.target, method)(*args, **kwargs)
    
    def __repr__(self):
        return f"Binding({self.name}: {self.source_interface} -> {self.target_interface}, type={self.binding_type.value})"


class BindingManager:
    """绑定管理器"""
    
    def __init__(self):
        self._bindings: Dict[str, Binding] = {}
    
    def add_binding(self, binding: Binding) -> Binding:
        """添加绑定"""
        self._bindings[binding.name] = binding
        return binding
    
    def remove_binding(self, name: str) -> Optional[Binding]:
        """移除绑定"""
        return self._bindings.pop(name, None)
    
    def get_binding(self, name: str) -> Optional[Binding]:
        """获取绑定"""
        return self._bindings.get(name)
    
    def find_bindings(self, source: Any = None, target: Any = None) -> list[Binding]:
        """查找绑定"""
        results = []
        for binding in self._bindings.values():
            if source and binding.source != source:
                continue
            if target and binding.target != target:
                continue
            results.append(binding)
        return results
    
    def list_bindings(self) -> list[Binding]:
        """列出所有绑定"""
        return list(self._bindings.values())
    
    def clear(self):
        """清除所有绑定"""
        self._bindings.clear()


class EventBinding(Binding):
    """事件绑定 - 支持发布/订阅模式"""
    
    def __init__(self, name: str, source: Any, source_interface: str, target: Any, target_interface: str):
        super().__init__(name, source, source_interface, target, target_interface, BindingType.EVENT)
        self._subscribers: Dict[str, list] = {}
    
    def subscribe(self, event: str, callback: Callable):
        """订阅事件"""
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(callback)
    
    def unsubscribe(self, event: str, callback: Callable):
        """取消订阅"""
        if event in self._subscribers:
            self._subscribers[event] = [cb for cb in self._subscribers[event] if cb != callback]
    
    def publish(self, event: str, data: Any):
        """发布事件"""
        if event in self._subscribers:
            for callback in self._subscribers[event]:
                callback(data)
