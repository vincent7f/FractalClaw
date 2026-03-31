"""
Learning 组件 - 学习组件

实现智能体的自我进化能力
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import random

from ..core.component import Component, ClientInterface, ServiceInterface


class LearningType(Enum):
    """学习类型"""
    SUPERVISED = "supervised"       # 监督学习
    REINFORCEMENT = "reinforcement"  # 强化学习
    IMITATION = "imitation"          # 模仿学习
    META = "meta"                    # 元学习
    EVOLUTIONARY = "evolutionary"   # 进化学习


@dataclass
class Experience:
    """经验"""
    state: Any
    action: Any
    reward: float
    next_state: Any
    done: bool
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LearnedSkill:
    """学习到的技能"""
    id: str
    name: str
    description: str
    pattern: str              # 匹配模式
    response: str              # 响应模板
    confidence: float = 0.0     # 置信度
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class EvolutionEngine:
    """
    进化引擎 - 负责智能体的自我进化
    
    支持:
    - 技能习得
    - 行为优化
    - 结构演化
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._skills: Dict[str, LearnedSkill] = {}
        self._experiences: List[Experience] = []
        self._evolution_rules: List[Callable] = []
    
    def add_skill(self, skill: LearnedSkill):
        """添加技能"""
        self._skills[skill.id] = skill
    
    def get_skill(self, skill_id: str) -> Optional[LearnedSkill]:
        """获取技能"""
        return self._skills.get(skill_id)
    
    def find_skill_by_pattern(self, pattern: str) -> Optional[LearnedSkill]:
        """根据模式查找技能"""
        pattern_lower = pattern.lower()
        best_match = None
        best_confidence = 0.0
        
        for skill in self._skills.values():
            if pattern_lower in skill.pattern.lower() or skill.pattern.lower() in pattern_lower:
                if skill.confidence > best_confidence:
                    best_confidence = skill.confidence
                    best_match = skill
        
        return best_match
    
    def learn_from_interaction(self, prompt: str, result: Dict[str, Any]):
        """从交互中学习"""
        # 提取有效的响应模式
        if result.get("success"):
            # 创建新的技能或更新现有技能
            skill = LearnedSkill(
                id=f"skill_{len(self._skills)}",
                name=f"Skill_{len(self._skills)}",
                description=f"Learned from: {prompt[:50]}",
                pattern=prompt[:100],
                response=str(result),
                confidence=0.5,
                usage_count=0,
                success_rate=1.0
            )
            self.add_skill(skill)
    
    def evolve(self):
        """
        触发进化
        
        可能的进化方向:
        1. 技能合并 - 将相似的技能合并
        2. 技能优化 - 提高技能的置信度
        3. 技能淘汰 - 移除低置信度技能
        """
        # 简单的进化策略
        to_remove = []
        
        for skill_id, skill in self._skills.items():
            # 淘汰低置信度技能
            if skill.confidence < 0.1:
                to_remove.append(skill_id)
        
        for skill_id in to_remove:
            del self._skills[skill_id]
        
        # 优化高使用率技能
        for skill in self._skills.values():
            if skill.usage_count > 10:
                skill.confidence = min(1.0, skill.confidence + 0.05)
        
        return {
            "skills_count": len(self._skills),
            "removed": len(to_remove),
            "evolved": len(self._skills) - len(to_remove)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_skills": len(self._skills),
            "avg_confidence": sum(s.confidence for s in self._skills.values()) / max(1, len(self._skills)),
            "total_experiences": len(self._experiences),
        }


class LearningComponent(Component):
    """
    学习组件 - 负责智能体的学习和进化
    
    支持:
    - 经验积累
    - 技能习得
    - 自我进化
    - 行为优化
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(name)
        self.config = config or {}
        self._evolution_engine = EvolutionEngine(self.config)
        self._learning_enabled = True
        self._experience_buffer: List[Experience] = []
        self._max_buffer_size = 1000
        
        # 定义接口
        self.add_interface(ServiceInterface("learning_interface", [
            "learn", "evolve", "get_skills", "get_stats"
        ]))
        self.add_interface(ClientInterface("client_interface", []))
    
    def learn(self, prompt: str, result: Dict[str, Any]):
        """
        学习从交互中
        
        Args:
            prompt: 用户输入
            result: 执行结果
        """
        if not self._learning_enabled:
            return
        
        # 提取经验
        experience = Experience(
            state=prompt,
            action=result.get("action", ""),
            reward=1.0 if result.get("success") else -1.0,
            next_state=str(result),
            done=True
        )
        
        self._experience_buffer.append(experience)
        
        # 保持缓冲区大小
        if len(self._experience_buffer) > self._max_buffer_size:
            self._experience_buffer = self._experience_buffer[-self._max_buffer_size:]
        
        # 让进化引擎学习
        self._evolution_engine.learn_from_interaction(prompt, result)
    
    def evolve(self) -> Dict[str, Any]:
        """
        触发自我进化
        """
        return self._evolution_engine.evolve()
    
    def get_skills(self) -> List[Dict[str, Any]]:
        """获取所有技能"""
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "pattern": s.pattern,
                "confidence": s.confidence,
                "usage_count": s.usage_count,
                "success_rate": s.success_rate,
            }
            for s in self._evolution_engine._skills.values()
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取学习统计"""
        return self._evolution_engine.get_stats()
    
    def enable_learning(self):
        """启用学习"""
        self._learning_enabled = True
    
    def disable_learning(self):
        """禁用学习"""
        self._learning_enabled = False
    
    def add_evolution_rule(self, rule: Callable):
        """添加进化规则"""
        self._evolution_engine._evolution_rules.append(rule)
    
    def apply_evolution_rules(self):
        """应用进化规则"""
        results = []
        for rule in self._evolution_engine._evolution_rules:
            try:
                result = rule(self)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        return results
    
    def _on_initialize(self):
        pass
    
    def _on_start(self):
        pass
    
    def _on_stop(self):
        pass
