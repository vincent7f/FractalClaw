"""
Capability 组件 - 能力系统

实现智能体的能力管理
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class CapabilityLevel(Enum):
    """能力等级"""
    NONE = 0
    BASIC = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4


@dataclass
class Capability:
    """
    能力定义
    """
    id: str
    name: str
    description: str
    level: CapabilityLevel = CapabilityLevel.BASIC
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "level": self.level.name,
            "tags": self.tags,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class CapabilityInstance:
    """能力实例"""
    capability: Capability
    instance_id: str
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    success_count: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count


class CapabilityRegistry:
    """
    能力注册表
    
    管理智能体的所有能力
    """
    
    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._instances: Dict[str, CapabilityInstance] = {}
        self._providers: Dict[str, Callable] = {}
    
    def register_capability(self, capability: Capability):
        """注册能力"""
        self._capabilities[capability.id] = capability
    
    def unregister_capability(self, capability_id: str) -> Optional[Capability]:
        """注销能力"""
        return self._capabilities.pop(capability_id, None)
    
    def get_capability(self, capability_id: str) -> Optional[Capability]:
        """获取能力"""
        return self._capabilities.get(capability_id)
    
    def list_capabilities(self, tags: Optional[List[str]] = None) -> List[Capability]:
        """列出能力"""
        capabilities = list(self._capabilities.values())
        
        if tags:
            capabilities = [
                c for c in capabilities 
                if any(t in c.tags for t in tags)
            ]
        
        return capabilities
    
    def find_capability(self, query: str) -> Optional[Capability]:
        """查找能力"""
        query_lower = query.lower()
        
        for capability in self._capabilities.values():
            if query_lower in capability.name.lower():
                return capability
            if query_lower in capability.description.lower():
                return capability
        
        return None
    
    def enable_capability(self, capability_id: str):
        """启用能力"""
        capability = self._capabilities.get(capability_id)
        if capability:
            capability.enabled = True
    
    def disable_capability(self, capability_id: str):
        """禁用能力"""
        capability = self._capabilities.get(capability_id)
        if capability:
            capability.enabled = False
    
    def register_provider(self, name: str, provider: Callable):
        """注册能力提供者"""
        self._providers[name] = provider
    
    def get_provider(self, name: str) -> Optional[Callable]:
        """获取能力提供者"""
        return self._providers.get(name)
    
    def create_instance(self, capability_id: str, config: Optional[Dict[str, Any]] = None) -> Optional[CapabilityInstance]:
        """创建能力实例"""
        import uuid
        capability = self._capabilities.get(capability_id)
        
        if not capability:
            return None
        
        instance = CapabilityInstance(
            capability=capability,
            instance_id=str(uuid.uuid4()),
            config=config or {}
        )
        
        self._instances[instance.instance_id] = instance
        return instance
    
    def record_usage(self, instance_id: str, success: bool):
        """记录使用"""
        instance = self._instances.get(instance_id)
        if instance:
            instance.usage_count += 1
            if success:
                instance.success_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_capabilities": len(self._capabilities),
            "enabled_capabilities": sum(1 for c in self._capabilities.values() if c.enabled),
            "total_instances": len(self._instances),
            "avg_success_rate": sum(i.success_rate for i in self._instances.values()) / max(1, len(self._instances)),
        }
