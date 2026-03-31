"""
定时任务调度器

基于 APScheduler 实现定时任务管理
"""

from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import uuid

from fractalclaw.core.component import Component, LeafComponent, ComponentState


class ScheduleType(Enum):
    """调度类型"""
    DATE = "date"          # 一次性执行
    INTERVAL = "interval"  # 间隔执行
    CRON = "cron"         # Cron 表达式


class JobStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """任务定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    func: str = ""           # 函数名
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    schedule_type: ScheduleType = ScheduleType.DATE
    schedule_config: Dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_result: Any = None
    error: str = ""
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "func": self.func,
            "schedule_type": self.schedule_type.value,
            "schedule_config": self.schedule_config,
            "status": self.status.value,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "enabled": self.enabled,
        }


# 任务执行器类型
JobExecutor = Callable[..., Awaitable[Any]]


class TaskScheduler(LeafComponent):
    """
    任务调度器
    
    提供定时任务管理能力，支持:
    - 一次性任务
    - 间隔任务
    - Cron 任务
    """

    def __init__(self, name: str = "scheduler", timezone: str = "UTC"):
        super().__init__(name)
        self.timezone = timezone
        
        self._jobs: Dict[str, Job] = {}
        self._executors: Dict[str, JobExecutor] = {}
        self._scheduler = None
        self._running = False

    # ==================== 生命周期 ====================

    def _on_initialize(self):
        """初始化调度器"""
        self._init_scheduler()

    def _on_start(self):
        """启动调度器"""
        self._running = True
        for job in self._jobs.values():
            if job.enabled and job.status == JobStatus.PENDING:
                self._schedule_job(job)

    def _on_stop(self):
        """停止调度器"""
        self._running = False
        if self._scheduler:
            self._scheduler.shutdown()

    def _init_scheduler(self):
        """初始化 APScheduler"""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            
            self._scheduler = AsyncIOScheduler(
                timezone=self.timezone,
                job_defaults={
                    "coalesce": False,
                    "max_instances": 1,
                    "misfire_grace_time": 60,
                },
            )
        except ImportError:
            print("APScheduler not installed. Install with: pip install apscheduler")

    # ==================== 任务管理 ====================

    def add_job(
        self,
        name: str,
        func: str,
        schedule_type: ScheduleType,
        schedule_config: Dict[str, Any],
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """添加任务"""
        job = Job(
            name=name,
            func=func,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            args=args or [],
            kwargs=kwargs or {},
        )
        
        self._jobs[job.id] = job
        
        if self._running and job.enabled:
            self._schedule_job(job)
        
        return job

    def remove_job(self, job_id: str) -> bool:
        """移除任务"""
        job = self._jobs.pop(job_id, None)
        
        if job and self._scheduler:
            try:
                self._scheduler.remove_job(job_id)
            except:
                pass
        
        return job is not None

    def get_job(self, job_id: str) -> Optional[Job]:
        """获取任务"""
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[Job]:
        """列出所有任务"""
        return list(self._jobs.values())

    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        job = self._jobs.get(job_id)
        if job:
            job.enabled = False
            if self._scheduler:
                try:
                    self._scheduler.pause_job(job_id)
                except:
                    pass
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        job = self._jobs.get(job_id)
        if job:
            job.enabled = True
            if self._running and self._scheduler:
                self._schedule_job(job)
            return True
        return False

    # ==================== 便捷方法 ====================

    def add_date_job(
        self,
        name: str,
        func: str,
        run_date: datetime,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """添加一次性任务"""
        return self.add_job(
            name=name,
            func=func,
            schedule_type=ScheduleType.DATE,
            schedule_config={"run_date": run_date},
            args=args,
            kwargs=kwargs,
        )

    def add_interval_job(
        self,
        name: str,
        func: str,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """添加间隔任务"""
        return self.add_job(
            name=name,
            func=func,
            schedule_type=ScheduleType.INTERVAL,
            schedule_config={
                "seconds": seconds,
                "minutes": minutes,
                "hours": hours,
            },
            args=args,
            kwargs=kwargs,
        )

    def add_cron_job(
        self,
        name: str,
        func: str,
        cron: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """添加 Cron 任务"""
        # 解析 cron 表达式
        # 格式: "minute hour day month weekday"
        parts = cron.split()
        config = {}
        
        if len(parts) >= 1:
            config["minute"] = parts[0]
        if len(parts) >= 2:
            config["hour"] = parts[1]
        if len(parts) >= 3:
            config["day"] = parts[2]
        if len(parts) >= 4:
            config["month"] = parts[3]
        if len(parts) >= 5:
            config["day_of_week"] = parts[4]
        
        return self.add_job(
            name=name,
            func=func,
            schedule_type=ScheduleType.CRON,
            schedule_config=config,
            args=args,
            kwargs=kwargs,
        )

    # ==================== 调度执行 ====================

    def _schedule_job(self, job: Job):
        """调度任务"""
        if not self._scheduler:
            return
        
        if job.schedule_type == ScheduleType.DATE:
            self._scheduler.add_job(
                self._execute_job,
                "date",
                run_date=job.schedule_config.get("run_date"),
                id=job.id,
                args=[job.id],
            )
            
        elif job.schedule_type == ScheduleType.INTERVAL:
            config = job.schedule_config
            self._scheduler.add_job(
                self._execute_job,
                "interval",
                seconds=config.get("seconds", 0),
                minutes=config.get("minutes", 0),
                hours=config.get("hours", 0),
                id=job.id,
                args=[job.id],
            )
            
        elif job.schedule_type == ScheduleType.CRON:
            config = job.schedule_config
            self._scheduler.add_job(
                self._execute_job,
                "cron",
                **config,
                id=job.id,
                args=[job.id],
            )

    async def _execute_job(self, job_id: str):
        """执行任务"""
        job = self._jobs.get(job_id)
        if not job:
            return
        
        job.status = JobStatus.RUNNING
        job.last_run = datetime.now()
        
        try:
            # 查找执行器
            executor = self._executors.get(job.func)
            
            if executor:
                result = await executor(job.args, job.kwargs)
                job.last_result = result
                job.status = JobStatus.COMPLETED
            else:
                job.error = f"No executor found for {job.func}"
                job.status = JobStatus.FAILED
                
        except Exception as e:
            job.error = str(e)
            job.status = JobStatus.FAILED

    # ==================== 执行器管理 ====================

    def register_executor(self, func_name: str, executor: JobExecutor):
        """注册任务执行器"""
        self._executors[func_name] = executor

    # ==================== 工具方法 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计"""
        return {
            "jobs_count": len(self._jobs),
            "running": self._running,
            "jobs": [j.to_dict() for j in self._jobs.values()],
        }
