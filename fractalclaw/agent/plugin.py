"""
Plugin 组件 - 插件系统

实现 OpenClaw 的可扩展插件架构
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import importlib
import os


@dataclass
class PluginMetadata:
    """插件元数据"""
    id: str
    name: str
    version: str
    description: str
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class Plugin(ABC):
    """
    插件基类
    
    所有插件必须继承此类
    """
    
    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self._enabled = False
        self._agent = None
    
    @abstractmethod
    def initialize(self, agent: Any):
        """初始化插件"""
        pass
    
    @abstractmethod
    def enable(self):
        """启用插件"""
        pass
    
    @abstractmethod
    def disable(self):
        """禁用插件"""
        pass
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    def on_message(self, message: Any) -> Any:
        """消息钩子"""
        return message
    
    def on_action(self, action: str, params: Dict[str, Any]) -> Any:
        """动作钩子"""
        pass
    
    def get_extensions(self) -> Dict[str, Callable]:
        """获取扩展"""
        return {}


class PluginManager:
    """
    插件管理器
    
    负责插件的加载、卸载、启用、禁用
    """
    
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[Callable]] = {}
    
    def register_plugin(self, plugin: Plugin) -> Plugin:
        """注册插件"""
        self._plugins[plugin.metadata.id] = plugin
        return plugin
    
    def unregister_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """注销插件"""
        return self._plugins.pop(plugin_id, None)
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """获取插件"""
        return self._plugins.get(plugin_id)
    
    def list_plugins(self) -> List[PluginMetadata]:
        """列出所有插件"""
        return [p.metadata for p in self._plugins.values()]
    
    def enable_plugin(self, plugin_id: str, agent: Any = None) -> bool:
        """启用插件"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        try:
            if agent:
                plugin._agent = agent
                plugin.initialize(agent)
            plugin.enable()
            return True
        except Exception:
            return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        try:
            plugin.disable()
            return True
        except Exception:
            return False
    
    def load_plugins_from_directory(self, directory: str, agent: Any = None):
        """从目录加载插件"""
        if not os.path.exists(directory):
            return
        
        for filename in os.listdir(directory):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(module_name)
                    
                    # 查找插件类
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, Plugin) and attr != Plugin:
                            plugin = attr(PluginMetadata(
                                id=module_name,
                                name=module_name,
                                version="1.0.0",
                                description=f"Loaded from {filename}"
                            ))
                            self.register_plugin(plugin)
                            if agent:
                                self.enable_plugin(module_name, agent)
                            
                except Exception as e:
                    print(f"Failed to load plugin {module_name}: {e}")
    
    def register_hook(self, hook_name: str, callback: Callable):
        """注册钩子"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)
    
    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """触发钩子"""
        results = []
        for callback in self._hooks.get(hook_name, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception:
                pass
        return results
