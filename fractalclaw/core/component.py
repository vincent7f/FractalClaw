"""
Fractal 组件模型核心实现

参考 https://fractal.ow2.io/ 架构设计
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set, Type
from dataclasses import dataclass, field
from enum import Enum
import inspect
import uuid
from datetime import datetime


class ComponentState(Enum):
    """组件状态"""
    CREATED = "created"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ComponentMetadata:
    """组件元数据"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    state: ComponentState = ComponentState.CREATED
    attributes: Dict[str, Any] = field(default_factory=dict)


class Interface(ABC):
    """组件接口定义"""
    
    def __init__(self, name: str, methods: Optional[List[str]] = None):
        self.name = name
        self.methods = methods or []
    
    def __repr__(self):
        return f"Interface({self.name}, methods={self.methods})"


class ServiceInterface(Interface):
    """服务接口 - 组件提供的服务"""
    pass


class ClientInterface(Interface):
    """客户端接口 - 组件需要的依赖"""
    pass


class Component(ABC):
    """
    Fractal 组件基类
    
    核心特性:
    - 递归性: 组件可以嵌套
    - 反射性: 具备内省和干预能力
    - 开放性: 通过 membrane 定制非功能性服务
    """
    
    def __init__(self, name: str, metadata: Optional[ComponentMetadata] = None):
        self.name = name
        self.metadata = metadata or ComponentMetadata(name=name)
        self._parent: Optional[CompositeComponent] = None
        self._membrane: Optional['Membrane'] = None
        self._interfaces: Dict[str, Interface] = {}
        self._bindings: List['Binding'] = []
        self._controller = ComponentController(self)
    
    @property
    def id(self) -> str:
        return self.metadata.id
    
    @property
    def state(self) -> ComponentState:
        return self.metadata.state
    
    @property
    def parent(self) -> Optional['CompositeComponent']:
        return self._parent
    
    @property
    def membrane(self) -> Optional['Membrane']:
        return self._membrane
    
    @membrane.setter
    def membrane(self, value: 'Membrane'):
        self._membrane = value
    
    def set_parent(self, parent: Optional['CompositeComponent']):
        self._parent = parent
    
    def add_interface(self, interface: Interface):
        """添加接口"""
        self._interfaces[interface.name] = interface
    
    def get_interface(self, name: str) -> Optional[Interface]:
        """获取接口"""
        return self._interfaces.get(name)
    
    def list_interfaces(self) -> List[Interface]:
        """列出所有接口"""
        return list(self._interfaces.values())
    
    def add_binding(self, binding: 'Binding'):
        """添加绑定"""
        self._bindings.append(binding)
    
    def remove_binding(self, binding: 'Binding'):
        """移除绑定"""
        if binding in self._bindings:
            self._bindings.remove(binding)
    
    def list_bindings(self) -> List['Binding']:
        """列出所有绑定"""
        return self._bindings.copy()
    
    # ==================== 生命周期方法 ====================
    
    def initialize(self):
        """初始化组件"""
        if self.state != ComponentState.CREATED:
            return
        self.metadata.state = ComponentState.INITIALIZED
        self._on_initialize()
    
    def start(self):
        """启动组件"""
        if self.state != ComponentState.INITIALIZED:
            return
        self.metadata.state = ComponentState.STARTED
        self._on_start()
    
    def stop(self):
        """停止组件"""
        if self.state != ComponentState.STARTED:
            return
        self._on_stop()
        self.metadata.state = ComponentState.STOPPED
    
    def destroy(self):
        """销毁组件"""
        self._on_destroy()
        self._parent = None
        self._membrane = None
    
    # ==================== 可覆盖的钩子方法 ====================
    
    def _on_initialize(self):
        """初始化钩子 - 子类可覆盖"""
        pass
    
    def _on_start(self):
        """启动钩子 - 子类可覆盖"""
        pass
    
    def _on_stop(self):
        """停止钩子 - 子类可覆盖"""
        pass
    
    def _on_destroy(self):
        """销毁钩子 - 子类可覆盖"""
        pass
    
    # ==================== 反射/内省能力 ====================
    
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """获取属性 - 反射读取"""
        return self.metadata.attributes.get(name, default)
    
    def set_attribute(self, name: str, value: Any):
        """设置属性 - 反射写入"""
        self.metadata.attributes[name] = value
    
    def list_attributes(self) -> Dict[str, Any]:
        """列出所有属性"""
        return self.metadata.attributes.copy()
    
    def invoke(self, method: str, *args, **kwargs) -> Any:
        """调用方法 - 反射调用"""
        if hasattr(self, method):
            return getattr(self, method)(*args, **kwargs)
        raise AttributeError(f"Component {self.name} has no method {method}")
    
    def get_type_info(self) -> Dict[str, Any]:
        """获取类型信息"""
        return {
            "name": self.__class__.__name__,
            "module": self.__class__.__module__,
            "doc": self.__class__.__doc__,
            "methods": [m for m in dir(self) if callable(getattr(self, m)) and not m.startswith('_')],
            "interfaces": [i.name for i in self._interfaces.values()],
        }
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r}, state={self.state.value})"


class LeafComponent(Component):
    """叶子组件 - 不包含子组件的基础组件"""
    
    def __init__(self, name: str, implementation: Any = None):
        super().__init__(name)
        self.implementation = implementation


class CompositeComponent(Component):
    """
    复合组件 - 可以包含子组件
    
    实现递归组合特性
    """
    
    def __init__(self, name: str, metadata: Optional[ComponentMetadata] = None):
        super().__init__(name, metadata)
        self._children: Dict[str, Component] = {}
    
    def add_child(self, component: Component) -> Component:
        """添加子组件"""
        if component.name in self._children:
            raise ValueError(f"Component {component.name} already exists")
        component.set_parent(self)
        self._children[component.name] = component
        return component
    
    def remove_child(self, name: str) -> Optional[Component]:
        """移除子组件"""
        component = self._children.pop(name, None)
        if component:
            component.set_parent(None)
        return component
    
    def get_child(self, name: str) -> Optional[Component]:
        """获取子组件"""
        return self._children.get(name)
    
    def list_children(self) -> List[Component]:
        """列出所有子组件"""
        return list(self._children.values())
    
    def find_child(self, predicate) -> Optional[Component]:
        """查找子组件"""
        for child in self._children.values():
            if predicate(child):
                return child
            if isinstance(child, CompositeComponent):
                found = child.find_child(predicate)
                if found:
                    return found
        return None
    
    def find_children(self, predicate) -> List[Component]:
        """查找所有匹配的子组件"""
        results = []
        for child in self._children.values():
            if predicate(child):
                results.append(child)
            if isinstance(child, CompositeComponent):
                results.extend(child.find_children(predicate))
        return results
    
    def _on_initialize(self):
        """初始化所有子组件"""
        for child in self._children.values():
            if child.state == ComponentState.CREATED:
                child.initialize()
    
    def _on_start(self):
        """启动所有子组件"""
        for child in self._children.values():
            if child.state == ComponentState.INITIALIZED:
                child.start()
    
    def _on_stop(self):
        """停止所有子组件"""
        for child in self._children.values():
            if child.state == ComponentState.STARTED:
                child.stop()
    
    def _on_destroy(self):
        """销毁所有子组件"""
        for child in list(self._children.values()):
            child.destroy()
        self._children.clear()


class ComponentController:
    """组件控制器 - 提供对组件的控制能力"""
    
    def __init__(self, component: Component):
        self.component = component
    
    def get_info(self) -> Dict[str, Any]:
        """获取组件信息"""
        return {
            "id": self.component.id,
            "name": self.component.name,
            "type": self.component.__class__.__name__,
            "state": self.component.state.value,
            "parent": self.component.parent.name if self.component.parent else None,
            "children_count": len(self.component.list_children()) if isinstance(self.component, CompositeComponent) else 0,
            "interfaces": [i.name for i in self.component.list_interfaces()],
            "bindings_count": len(self.component.list_bindings()),
        }
    
    def get_all_info(self) -> Dict[str, Any]:
        """获取完整信息（包括子组件）"""
        info = self.get_info()
        if isinstance(self.component, CompositeComponent):
            info["children"] = [
                ComponentController(child).get_all_info() 
                for child in self.component.list_children()
            ]
        return info
