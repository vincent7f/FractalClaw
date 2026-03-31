"""
内省模块 - 提供组件的自检能力

Fractal 的反射性特性实现
"""

from typing import Any, Dict, List, Optional, Callable, Type
from dataclasses import dataclass
from datetime import datetime
import inspect
import json


@dataclass
class IntrospectionResult:
    """内省结果"""
    component_id: str
    component_name: str
    component_type: str
    state: str
    interfaces: List[str]
    attributes: Dict[str, Any]
    methods: List[str]
    children: List['IntrospectionResult']
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_name": self.component_name,
            "component_type": self.component_type,
            "state": self.state,
            "interfaces": self.interfaces,
            "attributes": self.attributes,
            "methods": self.methods,
            "children": [c.to_dict() for c in self.children],
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class Introspectable:
    """可内省的接口"""
    
    def introspect(self) -> IntrospectionResult:
        """执行内省"""
        raise NotImplementedError


class Introspection:
    """
    内省器 - 提供组件的自检能力
    
    支持:
    - 检查组件结构
    - 检查组件状态
    - 修改组件行为
    - 动态调用方法
    """
    
    def __init__(self, component: Any):
        self.component = component
    
    def inspect(self) -> IntrospectionResult:
        """执行完整内省"""
        from .component import Component, CompositeComponent
        
        if not isinstance(self.component, Component):
            return self._inspect_generic()
        
        # 内省 Fractal 组件
        result = IntrospectionResult(
            component_id=self.component.id,
            component_name=self.component.name,
            component_type=self.component.__class__.__name__,
            state=self.component.state.value,
            interfaces=[i.name for i in self.component.list_interfaces()],
            attributes=self.component.list_attributes(),
            methods=self._get_methods(),
            children=self._inspect_children() if isinstance(self.component, CompositeComponent) else [],
        )
        return result
    
    def _inspect_generic(self) -> IntrospectionResult:
        """内省通用对象"""
        return IntrospectionResult(
            component_id=id(self.component),
            component_name=getattr(self.component, '__name__', str(type(self.component))),
            component_type=type(self.component).__name__,
            state="unknown",
            interfaces=[],
            attributes={},
            methods=self._get_methods(),
            children=[],
        )
    
    def _inspect_children(self) -> List[IntrospectionResult]:
        """内省子组件"""
        from .component import CompositeComponent
        
        results = []
        if isinstance(self.component, CompositeComponent):
            for child in self.component.list_children():
                results.append(Introspection(child).inspect())
        return results
    
    def _get_methods(self) -> List[str]:
        """获取组件方法"""
        methods = []
        for name in dir(self.component):
            if not name.startswith('_') and callable(getattr(self.component, name)):
                methods.append(name)
        return methods
    
    def get_method_signature(self, method_name: str) -> Optional[Dict[str, Any]]:
        """获取方法签名"""
        method = getattr(self.component, method_name, None)
        if method is None:
            return None
        
        try:
            sig = inspect.signature(method)
            return {
                "name": method_name,
                "signature": str(sig),
                "parameters": [
                    {
                        "name": p.name,
                        "default": str(p.default) if p.default != inspect.Parameter.empty else None,
                        "kind": str(p.kind),
                    }
                    for p in sig.parameters.values()
                ],
                "is_async": inspect.iscoroutinefunction(method),
            }
        except (ValueError, TypeError):
            return {"name": method_name, "signature": "unknown"}
    
    def list_callable_methods(self, include_private: bool = False) -> List[str]:
        """列出可调用方法"""
        methods = []
        for name in dir(self.component):
            if include_private or not name.startswith('_'):
                attr = getattr(self.component, name, None)
                if callable(attr):
                    methods.append(name)
        return methods
    
    def invoke_method(self, method_name: str, *args, **kwargs) -> Any:
        """动态调用方法"""
        method = getattr(self.component, method_name, None)
        if method is None:
            raise AttributeError(f"No method {method_name}")
        return method(*args, **kwargs)
    
    def get_attribute(self, attr_name: str, default: Any = None) -> Any:
        """获取属性"""
        return getattr(self.component, attr_name, default)
    
    def set_attribute(self, attr_name: str, value: Any):
        """设置属性"""
        setattr(self.component, attr_name, value)
    
    def has_method(self, method_name: str) -> bool:
        """检查是否有方法"""
        return hasattr(self.component, method_name) and callable(getattr(self.component, method_name))
    
    def get_doc(self) -> Optional[str]:
        """获取文档"""
        return self.component.__doc__


class AdaptiveIntrospection(Introspection):
    """自适应内省 - 支持动态修改组件"""
    
    def patch_method(self, method_name: str, new_method: Callable):
        """修补方法"""
        setattr(self.component, method_name, new_method)
    
    def add_method(self, method_name: str, method: Callable):
        """添加方法"""
        setattr(self.component, method_name, method)
    
    def remove_method(self, method_name: str):
        """移除方法"""
        if hasattr(self.component, method_name):
            delattr(self.component, method_name)
    
    def inject_middleware(self, method_name: str, middleware: Callable):
        """注入中间件"""
        original = getattr(self.component, method_name, None)
        if original is None:
            raise AttributeError(f"No method {method_name}")
        
        def wrapped(*args, **kwargs):
            middleware(self.component, method_name, args, kwargs)
            return original(*args, **kwargs)
        
        setattr(self.component, method_name, wrapped)
