"""
ToolRegistry 组件 - 工具注册组件

负责工具的管理和发现
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ..core.component import Component, ServiceInterface, ClientInterface
from .executor import Tool, ToolType


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()


class ToolRegistryComponent(Component):
    """
    工具注册组件 - 管理和发现工具
    
    支持:
    - 工具注册/注销
    - 工具发现
    - 工具分类
    - 工具版本管理
    """
    
    def __init__(self, name: str):
        super().__init__(name)
        self._tools: Dict[str, Tool] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._categories: Dict[str, List[str]] = {}
        
        # 定义接口
        self.add_interface(ServiceInterface("tool_registry_interface", [
            "register_tool", "unregister_tool", "get_tool", "list_tools",
            "find_tools", "list_categories"
        ]))
        self.add_interface(ClientInterface("client_interface", []))
    
    def register_tool(
        self,
        tool: Tool,
        metadata: Optional[ToolMetadata] = None,
        category: Optional[str] = None
    ):
        """
        注册工具
        
        Args:
            tool: 工具对象
            metadata: 工具元数据
            category: 工具分类
        """
        self._tools[tool.name] = tool
        
        if metadata:
            self._metadata[tool.name] = metadata
        
        if category:
            if category not in self._categories:
                self._categories[category] = []
            if tool.name not in self._categories[category]:
                self._categories[category].append(tool.name)
    
    def unregister_tool(self, name: str) -> Optional[Tool]:
        """注销工具"""
        tool = self._tools.pop(name, None)
        self._metadata.pop(name, None)
        
        # 从分类中移除
        for category in self._categories:
            if name in self._categories[category]:
                self._categories[category].remove(name)
        
        return tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """列出所有工具"""
        return list(self._tools.keys())
    
    def list_tools_detail(self) -> List[Dict[str, Any]]:
        """列出所有工具详情"""
        results = []
        for name, tool in self._tools.items():
            info = tool.to_dict()
            if name in self._metadata:
                info["metadata"] = {
                    "version": self._metadata[name].version,
                    "author": self._metadata[name].author,
                    "tags": self._metadata[name].tags,
                }
            results.append(info)
        return results
    
    def find_tools(self, query: str) -> List[str]:
        """
        查找工具
        
        Args:
            query: 查询字符串
            
        Returns:
            匹配的工具列表
        """
        results = []
        query_lower = query.lower()
        
        for name, tool in self._tools.items():
            if query_lower in name.lower():
                results.append(name)
            elif query_lower in tool.description.lower():
                results.append(name)
            elif name in self._metadata:
                metadata = self._metadata[name]
                for tag in metadata.tags:
                    if query_lower in tag.lower():
                        results.append(name)
                        break
        
        return results
    
    def list_categories(self) -> List[str]:
        """列出所有分类"""
        return list(self._categories.keys())
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """获取分类下的工具"""
        return self._categories.get(category, [])
    
    def register_function_as_tool(
        self,
        name: str,
        description: str,
        func: Callable,
        category: Optional[str] = None
    ):
        """
        将函数注册为工具
        
        Args:
            name: 工具名称
            description: 工具描述
            func: 函数
            category: 分类
        """
        tool = Tool(
            name=name,
            description=description,
            type=ToolType.FUNCTION,
            handler=func
        )
        self.register_tool(tool, category=category)
    
    def _on_initialize(self):
        pass
    
    def _on_start(self):
        pass
    
    def _on_stop(self):
        pass
