#!/usr/bin/env python3
"""
工作流引擎
支持可视化工作流设计、任务执行和监控
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import uuid
import networkx as nx

from core.events import event_bus, BaseEvent
from core.results import ResultBuilder, ResultType

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskType(Enum):
    """任务类型"""
    SCRAPING = "scraping"
    RECOGNITION = "recognition"
    PROCESSING = "processing"
    EXPORT = "export"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


@dataclass
class TaskDefinition:
    """任务定义"""
    task_id: str
    name: str
    task_type: TaskType
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    timeout: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    condition: Optional[str] = None
    parallel: bool = False
    priority: int = 0


@dataclass
class TaskInstance:
    """任务实例"""
    task_id: str
    definition: TaskDefinition
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    logs: List[str] = field(default_factory=list)
    
    def start(self):
        """开始任务"""
        self.status = TaskStatus.RUNNING
        self.start_time = datetime.now()
    
    def complete(self, result: Any):
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.result = result
    
    def fail(self, error: str):
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        self.error = error
    
    def cancel(self):
        """取消任务"""
        self.status = TaskStatus.CANCELLED
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    workflow_id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    tasks: List[TaskDefinition] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    triggers: List[str] = field(default_factory=list)
    timeout: Optional[int] = None
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "name": task.name,
                    "task_type": task.task_type.value,
                    "parameters": task.parameters,
                    "dependencies": task.dependencies,
                    "timeout": task.timeout,
                    "max_retries": task.max_retries,
                    "condition": task.condition,
                    "parallel": task.parallel,
                    "priority": task.priority
                } for task in self.tasks
            ],
            "variables": self.variables,
            "triggers": self.triggers,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowDefinition':
        """从字典创建"""
        tasks = []
        for task_data in data.get("tasks", []):
            task = TaskDefinition(
                task_id=task_data["task_id"],
                name=task_data["name"],
                task_type=TaskType(task_data["task_type"]),
                parameters=task_data["parameters"],
                dependencies=task_data.get("dependencies", []),
                timeout=task_data.get("timeout"),
                max_retries=task_data.get("max_retries", 3),
                condition=task_data.get("condition"),
                parallel=task_data.get("parallel", False),
                priority=task_data.get("priority", 0)
            )
            tasks.append(task)
        
        return cls(
            workflow_id=data["workflow_id"],
            name=data["name"],
            description=data["description"],
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            tasks=tasks,
            variables=data.get("variables", {}),
            triggers=data.get("triggers", []),
            timeout=data.get("timeout"),
            max_retries=data.get("max_retries", 3)
        )


@dataclass
class WorkflowInstance:
    """工作流实例"""
    instance_id: str
    definition: WorkflowDefinition
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    task_instances: Dict[str, TaskInstance] = field(default_factory=dict)
    current_tasks: List[str] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    
    def start(self):
        """开始工作流"""
        self.status = TaskStatus.RUNNING
        self.start_time = datetime.now()
    
    def complete(self):
        """完成工作流"""
        self.status = TaskStatus.COMPLETED
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
    
    def fail(self):
        """工作流失败"""
        self.status = TaskStatus.FAILED
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()


class TaskExecutor(ABC):
    """任务执行器基类"""
    
    @abstractmethod
    async def execute(self, task: TaskInstance, context: Dict[str, Any]) -> Any:
        """执行任务"""
        pass
    
    @abstractmethod
    def supports_task_type(self, task_type: TaskType) -> bool:
        """检查是否支持该任务类型"""
        pass


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self):
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.workflow_instances: Dict[str, WorkflowInstance] = {}
        self.task_executors: Dict[TaskType, TaskExecutor] = {}
        self.running_instances: Dict[str, asyncio.Task] = {}
        
        # 统计信息
        self.stats = {
            "total_workflows": 0,
            "running_workflows": 0,
            "completed_workflows": 0,
            "failed_workflows": 0,
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0
        }
    
    def register_task_executor(self, task_type: TaskType, executor: TaskExecutor):
        """注册任务执行器"""
        self.task_executors[task_type] = executor
        logger.info(f"任务执行器已注册: {task_type.value} -> {executor.__class__.__name__}")
    
    def add_workflow_definition(self, definition: WorkflowDefinition) -> bool:
        """添加工作流定义"""
        try:
            # 验证工作流定义
            if not self._validate_workflow_definition(definition):
                return False
            
            self.workflow_definitions[definition.workflow_id] = definition
            logger.info(f"工作流定义已添加: {definition.name} ({definition.workflow_id})")
            return True
            
        except Exception as e:
            logger.error(f"添加工作流定义失败: {definition.name}, 错误: {e}")
            return False
    
    def _validate_workflow_definition(self, definition: WorkflowDefinition) -> bool:
        """验证工作流定义"""
        try:
            # 检查任务依赖关系
            task_ids = {task.task_id for task in definition.tasks}
            
            for task in definition.tasks:
                for dep_id in task.dependencies:
                    if dep_id not in task_ids:
                        logger.error(f"任务依赖不存在: {task.task_id} -> {dep_id}")
                        return False
            
            # 检查循环依赖
            if self._has_circular_dependency(definition.tasks):
                logger.error(f"工作流存在循环依赖: {definition.name}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"工作流定义验证失败: {e}")
            return False
    
    def _has_circular_dependency(self, tasks: List[TaskDefinition]) -> bool:
        """检查是否存在循环依赖"""
        try:
            # 构建依赖图
            G = nx.DiGraph()
            
            for task in tasks:
                G.add_node(task.task_id)
                for dep_id in task.dependencies:
                    G.add_edge(dep_id, task.task_id)
            
            # 检查是否有环
            return not nx.is_directed_acyclic_graph(G)
            
        except Exception as e:
            logger.warning(f"依赖关系检查失败: {e}")
            return False
    
    async def start_workflow(self, workflow_id: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """启动工作流"""
        if workflow_id not in self.workflow_definitions:
            raise ValueError(f"工作流定义不存在: {workflow_id}")
        
        definition = self.workflow_definitions[workflow_id]
        instance_id = f"{workflow_id}_{int(datetime.now().timestamp())}"
        
        # 创建工作流实例
        instance = WorkflowInstance(
            instance_id=instance_id,
            definition=definition,
            variables=variables or {}
        )
        
        # 创建任务实例
        for task_def in definition.tasks:
            task_instance = TaskInstance(task_id=task_def.task_id, definition=task_def)
            instance.task_instances[task_def.task_id] = task_instance
        
        # 注册实例
        self.workflow_instances[instance_id] = instance
        
        # 启动工作流执行
        task = asyncio.create_task(self._execute_workflow(instance))
        self.running_instances[instance_id] = task
        
        # 更新统计
        self.stats["total_workflows"] += 1
        self.stats["running_workflows"] += 1
        self.stats["total_tasks"] += len(definition.tasks)
        
        logger.info(f"工作流已启动: {definition.name} (实例: {instance_id})")
        return instance_id
    
    async def _execute_workflow(self, instance: WorkflowInstance):
        """执行工作流"""
        try:
            instance.start()
            
            # 获取可执行的任务
            executable_tasks = self._get_executable_tasks(instance)
            
            while executable_tasks and instance.status == TaskStatus.RUNNING:
                # 执行可执行的任务
                await self._execute_tasks(instance, executable_tasks)
                
                # 更新任务状态
                self._update_workflow_status(instance)
                
                # 获取新的可执行任务
                executable_tasks = self._get_executable_tasks(instance)
            
            # 工作流完成
            if instance.status == TaskStatus.RUNNING:
                if instance.failed_tasks:
                    instance.fail()
                    self.stats["failed_workflows"] += 1
                else:
                    instance.complete()
                    self.stats["completed_workflows"] += 1
                
                self.stats["running_workflows"] -= 1
            
            logger.info(f"工作流执行完成: {instance.definition.name} (实例: {instance.instance_id})")
            
        except Exception as e:
            logger.error(f"工作流执行异常: {instance.definition.name} (实例: {instance.instance_id}), 错误: {e}")
            instance.fail()
            self.stats["failed_workflows"] += 1
            self.stats["running_workflows"] -= 1
    
    def _get_executable_tasks(self, instance: WorkflowInstance) -> List[TaskInstance]:
        """获取可执行的任务"""
        executable_tasks = []
        
        for task_instance in instance.task_instances.values():
            if (task_instance.status == TaskStatus.PENDING and
                self._can_execute_task(task_instance, instance)):
                executable_tasks.append(task_instance)
        
        # 按优先级排序
        executable_tasks.sort(key=lambda t: t.definition.priority, reverse=True)
        return executable_tasks
    
    def _can_execute_task(self, task_instance: TaskInstance, instance: WorkflowInstance) -> bool:
        """检查任务是否可以执行"""
        # 检查依赖是否完成
        for dep_id in task_instance.definition.dependencies:
            dep_instance = instance.task_instances.get(dep_id)
            if not dep_instance or dep_instance.status != TaskStatus.COMPLETED:
                return False
        
        # 检查条件
        if task_instance.definition.condition:
            if not self._evaluate_condition(task_instance.definition.condition, instance.variables):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """评估条件表达式"""
        try:
            # 简单的条件评估，实际项目中可以使用更安全的表达式引擎
            # 这里仅作示例
            return eval(condition, {"__builtins__": {}}, variables)
        except Exception as e:
            logger.warning(f"条件评估失败: {condition}, 错误: {e}")
            return False
    
    async def _execute_tasks(self, instance: WorkflowInstance, tasks: List[TaskInstance]):
        """执行任务列表"""
        if not tasks:
            return
        
        # 检查是否有并行任务
        parallel_tasks = [t for t in tasks if t.definition.parallel]
        sequential_tasks = [t for t in tasks if not t.definition.parallel]
        
        # 执行并行任务
        if parallel_tasks:
            parallel_coros = [self._execute_single_task(instance, task) for task in parallel_tasks]
            await asyncio.gather(*parallel_coros, return_exceptions=True)
        
        # 执行串行任务
        for task in sequential_tasks:
            await self._execute_single_task(instance, task)
    
    async def _execute_single_task(self, instance: WorkflowInstance, task_instance: TaskInstance):
        """执行单个任务"""
        try:
            task_instance.start()
            instance.current_tasks.append(task_instance.task_id)
            
            # 查找执行器
            executor = self.task_executors.get(task_instance.definition.task_type)
            if not executor:
                raise ValueError(f"未找到任务执行器: {task_instance.definition.task_type.value}")
            
            # 构建执行上下文
            context = {
                "workflow_instance": instance,
                "variables": instance.variables,
                "task_results": {
                    tid: ti.result for tid, ti in instance.task_instances.items()
                    if ti.status == TaskStatus.COMPLETED
                }
            }
            
            # 执行任务
            result = await executor.execute(task_instance, context)
            
            # 任务完成
            task_instance.complete(result)
            instance.completed_tasks.append(task_instance.task_id)
            instance.current_tasks.remove(task_instance.task_id)
            
            # 更新统计
            self.stats["completed_tasks"] += 1
            
            logger.info(f"任务执行完成: {task_instance.definition.name} (实例: {instance.instance_id})")
            
        except Exception as e:
            # 任务失败
            error_msg = str(e)
            task_instance.fail(error_msg)
            instance.failed_tasks.append(task_instance.task_id)
            instance.current_tasks.remove(task_instance.task_id)
            
            # 更新统计
            self.stats["failed_tasks"] += 1
            
            logger.error(f"任务执行失败: {task_instance.definition.name} (实例: {instance.instance_id}), 错误: {error_msg}")
            
            # 检查是否需要重试
            if task_instance.retry_count < task_instance.definition.max_retries:
                task_instance.retry_count += 1
                task_instance.status = TaskStatus.PENDING
                logger.info(f"任务将重试: {task_instance.definition.name} (重试次数: {task_instance.retry_count})")
    
    def _update_workflow_status(self, instance: WorkflowInstance):
        """更新工作流状态"""
        total_tasks = len(instance.task_instances)
        completed_tasks = len(instance.completed_tasks)
        failed_tasks = len(instance.failed_tasks)
        
        if failed_tasks > 0 and instance.definition.max_retries <= 0:
            instance.fail()
        elif completed_tasks == total_tasks:
            instance.complete()
    
    def get_workflow_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """获取工作流实例"""
        return self.workflow_instances.get(instance_id)
    
    def get_workflow_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        instance = self.get_workflow_instance(instance_id)
        if not instance:
            return None
        
        return {
            "instance_id": instance.instance_id,
            "workflow_name": instance.definition.name,
            "status": instance.status.value,
            "start_time": instance.start_time.isoformat() if instance.start_time else None,
            "end_time": instance.end_time.isoformat() if instance.end_time else None,
            "duration": instance.duration,
            "progress": {
                "total_tasks": len(instance.task_instances),
                "completed_tasks": len(instance.completed_tasks),
                "failed_tasks": len(instance.failed_tasks),
                "running_tasks": len(instance.current_tasks)
            },
            "variables": instance.variables
        }
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """获取工作流统计信息"""
        return {
            **self.stats,
            "workflow_definitions": len(self.workflow_definitions),
            "workflow_instances": len(self.workflow_instances),
            "running_instances": len(self.running_instances)
        }
    
    def stop_workflow(self, instance_id: str) -> bool:
        """停止工作流"""
        if instance_id not in self.running_instances:
            return False
        
        try:
            # 取消执行任务
            task = self.running_instances[instance_id]
            task.cancel()
            
            # 更新实例状态
            instance = self.workflow_instances.get(instance_id)
            if instance:
                instance.fail()
                self.stats["failed_workflows"] += 1
                self.stats["running_workflows"] -= 1
            
            del self.running_instances[instance_id]
            
            logger.info(f"工作流已停止: {instance_id}")
            return True
            
        except Exception as e:
            logger.error(f"停止工作流失败: {instance_id}, 错误: {e}")
            return False
    
    async def shutdown(self):
        """关闭工作流引擎"""
        logger.info("正在关闭工作流引擎...")
        
        # 停止所有运行中的工作流
        for instance_id in list(self.running_instances.keys()):
            self.stop_workflow(instance_id)
        
        logger.info("工作流引擎已关闭")


# 全局工作流引擎实例
workflow_engine = WorkflowEngine()
