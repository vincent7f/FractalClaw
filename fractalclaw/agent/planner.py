"""
Planner 组件 - 规划组件

负责任务分解和规划
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from ..core.component import Component, ServiceInterface, ClientInterface


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    subtasks: List['Task'] = field(default_factory=list)
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.name,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "subtasks": [s.to_dict() for s in self.subtasks],
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


@dataclass
class Plan:
    """计划"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    tasks: List[Task] = field(default_factory=list)
    current_task_index: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_next_task(self) -> Optional[Task]:
        """获取下一个任务"""
        if self.current_task_index < len(self.tasks):
            return self.tasks[self.current_task_index]
        return None
    
    def advance(self):
        """推进到下一个任务"""
        self.current_task_index += 1
    
    def is_complete(self) -> bool:
        """是否完成"""
        return all(t.status == TaskStatus.COMPLETED for t in self.tasks)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "tasks": [t.to_dict() for t in self.tasks],
            "current_task_index": self.current_task_index,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
        }


class PlannerComponent(Component):
    """
    规划组件 - 负责任务分解和规划生成
    
    支持:
    - 任务分解
    - 依赖分析
    - 优先级排序
    - 计划执行
    """
    
    def __init__(self, name: str):
        super().__init__(name)
        self._plans: Dict[str, Plan] = {}
        self._current_plan: Optional[Plan] = None
        
        # 定义接口
        self.add_interface(ServiceInterface("planner_interface", [
            "create_plan", "execute_plan", "get_next_task", "get_plan"
        ]))
        self.add_interface(ClientInterface("client_interface", []))
    
    def create_plan(self, goal: str, context: Optional[List[Any]] = None) -> Plan:
        """
        创建计划
        
        Args:
            goal: 目标描述
            context: 上下文信息
            
        Returns:
            计划对象
        """
        plan = Plan(goal=goal)
        
        # 传递上下文信息给任务分解
        tasks = self._decompose(goal, context or [])
        plan.tasks = tasks
        
        self._plans[plan.id] = plan
        self._current_plan = plan
        
        return plan
    
    def _decompose(self, goal: str, context: List[Any]) -> List[Task]:
        """
        任务分解
        
        这是一个简单的实现，实际可以接入 LLM 进行智能分解
        context 参数可用于更智能的任务分解
        """
        tasks = []
        
        # 简单的关键词检测进行任务分解
        goal_lower = goal.lower()
        
        if "分析" in goal or "analyze" in goal_lower:
            tasks.append(Task(
                name="analyze",
                description="分析问题",
                priority=TaskPriority.HIGH
            ))
        
        if "搜索" in goal or "search" in goal_lower or "找" in goal:
            tasks.append(Task(
                name="search",
                description="搜索信息",
                priority=TaskPriority.HIGH
            ))
        
        if "总结" in goal or "summarize" in goal_lower:
            tasks.append(Task(
                name="summarize",
                description="总结信息",
                priority=TaskPriority.NORMAL
            ))
        
        if "执行" in goal or "execute" in goal_lower or "运行" in goal:
            tasks.append(Task(
                name="execute",
                description="执行操作",
                priority=TaskPriority.URGENT
            ))
        
        # 如果没有分解出任务，创建一个通用任务
        if not tasks:
            tasks.append(Task(
                name="process",
                description=f"处理: {goal}",
                priority=TaskPriority.NORMAL
            ))
        
        return tasks
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """获取计划"""
        return self._plans.get(plan_id)
    
    def get_current_plan(self) -> Optional[Plan]:
        """获取当前计划"""
        return self._current_plan
    
    def update_task_status(self, task_id: str, status: TaskStatus, result: Any = None, error: Optional[str] = None):
        """更新任务状态"""
        if not self._current_plan:
            return
        
        for task in self._current_plan.tasks:
            if task.id == task_id:
                task.status = status
                if result is not None:
                    task.result = result
                if error:
                    task.error = error
                if status == TaskStatus.RUNNING and not task.started_at:
                    task.started_at = datetime.now()
                if status == TaskStatus.COMPLETED and not task.completed_at:
                    task.completed_at = datetime.now()
                break
    
    def execute_plan(self) -> Plan:
        """执行计划"""
        if not self._current_plan:
            raise ValueError("No current plan")
        
        while not self._current_plan.is_complete():
            task = self._current_plan.get_next_task()
            if not task:
                break
            
            # 标记为运行中
            self.update_task_status(task.id, TaskStatus.RUNNING)
            
            # 这里会由 Executor 执行实际任务
            # 完成后由外部更新状态
        
        return self._current_plan
    
    def _on_initialize(self):
        pass
    
    def _on_start(self):
        pass
    
    def _on_stop(self):
        pass
