#!/usr/bin/env python3
"""
事件系统
实现事件驱动架构的核心，支持事件的发布、订阅和处理
"""

import asyncio
import logging
from typing import Dict, List, Any, Callable, Optional, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import uuid

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """事件优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class EventMetadata:
    """事件元数据"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3


class BaseEvent(ABC):
    """基础事件类"""
    
    def __init__(self, metadata: Optional[EventMetadata] = None):
        self.metadata = metadata or EventMetadata()
        self.metadata.source = self.__class__.__name__
    
    @property
    def event_type(self) -> str:
        """获取事件类型"""
        return self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": self.event_type,
            "metadata": {
                "event_id": self.metadata.event_id,
                "timestamp": self.metadata.timestamp.isoformat(),
                "source": self.metadata.source,
                "correlation_id": self.metadata.correlation_id,
                "priority": self.metadata.priority.value
            }
        }


# 具体事件定义
@dataclass
class ScrapingStartedEvent(BaseEvent):
    """采集开始事件"""
    channel_url: str
    max_posts: int
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "channel_url": self.channel_url,
            "max_posts": self.max_posts,
            "user_id": self.user_id
        })
        return base_dict


@dataclass
class ScrapingCompletedEvent(BaseEvent):
    """采集完成事件"""
    channel_url: str
    posts_count: int
    duration: float
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "channel_url": self.channel_url,
            "posts_count": self.posts_count,
            "duration": self.duration,
            "success": self.success,
            "error_message": self.error_message
        })
        return base_dict


@dataclass
class RecognitionStartedEvent(BaseEvent):
    """识别开始事件"""
    image_count: int
    ai_provider: str
    model: str
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "image_count": self.image_count,
            "ai_provider": self.ai_provider,
            "model": self.model
        })
        return base_dict


@dataclass
class RecognitionCompletedEvent(BaseEvent):
    """识别完成事件"""
    total_images: int
    hellokitty_count: int
    duration: float
    ai_provider: str
    model: str
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "total_images": self.total_images,
            "hellokitty_count": self.hellokitty_count,
            "duration": self.duration,
            "ai_provider": self.ai_provider,
            "model": self.model
        })
        return base_dict


@dataclass
class WorkflowStartedEvent(BaseEvent):
    """工作流开始事件"""
    workflow_id: str
    workflow_type: str
    parameters: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "parameters": self.parameters
        })
        return base_dict


@dataclass
class WorkflowCompletedEvent(BaseEvent):
    """工作流完成事件"""
    workflow_id: str
    workflow_type: str
    success: bool
    duration: float
    results: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "success": self.success,
            "duration": self.duration,
            "results": self.results
        })
        return base_dict


class EventHandler(ABC):
    """事件处理器基类"""
    
    @abstractmethod
    async def handle(self, event: BaseEvent) -> None:
        """处理事件"""
        pass
    
    @property
    @abstractmethod
    def event_types(self) -> List[Type[BaseEvent]]:
        """支持的事件类型"""
        pass
    
    @property
    def priority(self) -> EventPriority:
        """处理器优先级"""
        return EventPriority.NORMAL


class EventBus:
    """事件总线"""
    
    def __init__(self):
        self._handlers: Dict[Type[BaseEvent], List[EventHandler]] = {}
        self._middleware: List[Callable] = []
        self._event_history: List[BaseEvent] = []
        self._max_history_size = 1000
        
        # 统计信息
        self._stats = {
            "total_events": 0,
            "handled_events": 0,
            "failed_events": 0,
            "total_handlers": 0
        }
    
    def subscribe(self, event_type: Type[BaseEvent], handler: EventHandler) -> None:
        """订阅事件"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        self._stats["total_handlers"] += 1
        
        # 按优先级排序处理器
        self._handlers[event_type].sort(key=lambda h: h.priority.value, reverse=True)
        
        logger.info(f"事件处理器已订阅: {handler.__class__.__name__} -> {event_type.__name__}")
    
    def unsubscribe(self, event_type: Type[BaseEvent], handler: EventHandler) -> None:
        """取消订阅"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                self._stats["total_handlers"] -= 1
                logger.info(f"事件处理器已取消订阅: {handler.__class__.__name__} -> {event_type.__name__}")
            except ValueError:
                logger.warning(f"事件处理器未找到: {handler.__class__.__name__} -> {event_type.__name__}")
    
    def add_middleware(self, middleware: Callable) -> None:
        """添加中间件"""
        self._middleware.append(middleware)
        logger.info(f"中间件已添加: {middleware.__name__}")
    
    async def publish(self, event: BaseEvent) -> None:
        """发布事件"""
        try:
            # 记录事件历史
            self._event_history.append(event)
            if len(self._event_history) > self._max_history_size:
                self._event_history.pop(0)
            
            self._stats["total_events"] += 1
            
            # 应用中间件
            for middleware in self._middleware:
                event = await middleware(event)
                if event is None:
                    logger.info(f"事件被中间件过滤: {event.event_type}")
                    return
            
            # 查找处理器
            event_type = type(event)
            if event_type not in self._handlers:
                logger.debug(f"没有找到事件处理器: {event_type.__name__}")
                return
            
            # 并发处理事件
            handlers = self._handlers[event_type]
            tasks = []
            
            for handler in handlers:
                try:
                    task = asyncio.create_task(self._handle_event(handler, event))
                    tasks.append(task)
                except Exception as e:
                    logger.error(f"创建事件处理任务失败: {handler.__class__.__name__}, 错误: {e}")
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                self._stats["handled_events"] += 1
                
            logger.debug(f"事件已发布: {event.event_type} (ID: {event.metadata.event_id})")
            
        except Exception as e:
            self._stats["failed_events"] += 1
            logger.error(f"事件发布失败: {event.event_type}, 错误: {e}")
            raise
    
    async def _handle_event(self, handler: EventHandler, event: BaseEvent) -> None:
        """处理单个事件"""
        try:
            start_time = datetime.now()
            await handler.handle(event)
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.debug(f"事件处理完成: {handler.__class__.__name__} -> {event.event_type} (耗时: {duration:.3f}s)")
            
        except Exception as e:
            logger.error(f"事件处理失败: {handler.__class__.__name__} -> {event.event_type}, 错误: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "event_types": list(self._handlers.keys()),
            "history_size": len(self._event_history)
        }
    
    def get_event_history(self, event_type: Optional[Type[BaseEvent]] = None, limit: int = 100) -> List[BaseEvent]:
        """获取事件历史"""
        if event_type is None:
            return self._event_history[-limit:]
        else:
            return [e for e in self._event_history if isinstance(e, event_type)][-limit:]
    
    def clear_history(self) -> None:
        """清空事件历史"""
        self._event_history.clear()
        logger.info("事件历史已清空")


# 全局事件总线实例
event_bus = EventBus()


# 中间件示例
async def logging_middleware(event: BaseEvent) -> BaseEvent:
    """日志中间件"""
    logger.info(f"事件通过中间件: {event.event_type} (ID: {event.metadata.event_id})")
    return event


async def correlation_middleware(event: BaseEvent) -> BaseEvent:
    """关联ID中间件"""
    if not event.metadata.correlation_id:
        event.metadata.correlation_id = str(uuid.uuid4())
    return event


# 注册默认中间件
event_bus.add_middleware(logging_middleware)
event_bus.add_middleware(correlation_middleware)


# 事件处理器示例
class ScrapingEventHandler(EventHandler):
    """采集事件处理器"""
    
    @property
    def event_types(self) -> List[Type[BaseEvent]]:
        return [ScrapingStartedEvent, ScrapingCompletedEvent]
    
    async def handle(self, event: BaseEvent) -> None:
        if isinstance(event, ScrapingStartedEvent):
            await self._handle_scraping_started(event)
        elif isinstance(event, ScrapingCompletedEvent):
            await self._handle_scraping_completed(event)
    
    async def _handle_scraping_started(self, event: ScrapingStartedEvent) -> None:
        """处理采集开始事件"""
        logger.info(f"采集任务开始: {event.channel_url}, 最大帖子数: {event.max_posts}")
        # 这里可以添加业务逻辑，比如更新任务状态、发送通知等
    
    async def _handle_scraping_completed(self, event: ScrapingCompletedEvent) -> None:
        """处理采集完成事件"""
        if event.success:
            logger.info(f"采集任务完成: {event.channel_url}, 帖子数: {event.posts_count}, 耗时: {event.duration:.2f}s")
        else:
            logger.error(f"采集任务失败: {event.channel_url}, 错误: {event.error_message}")


class RecognitionEventHandler(EventHandler):
    """识别事件处理器"""
    
    @property
    def event_types(self) -> List[Type[BaseEvent]]:
        return [RecognitionStartedEvent, RecognitionCompletedEvent]
    
    async def handle(self, event: BaseEvent) -> None:
        if isinstance(event, RecognitionStartedEvent):
            await self._handle_recognition_started(event)
        elif isinstance(event, RecognitionCompletedEvent):
            await self._handle_recognition_completed(event)
    
    async def _handle_recognition_started(self, event: RecognitionStartedEvent) -> None:
        """处理识别开始事件"""
        logger.info(f"图片识别开始: {event.image_count} 张图片, AI提供商: {event.ai_provider}, 模型: {event.model}")
    
    async def _handle_recognition_completed(self, event: RecognitionCompletedEvent) -> None:
        """处理识别完成事件"""
        logger.info(f"图片识别完成: 总数 {event.total_images}, HelloKitty {event.hellokitty_count}, 耗时: {event.duration:.2f}s")


# 注册默认事件处理器
event_bus.subscribe(ScrapingStartedEvent, ScrapingEventHandler())
event_bus.subscribe(ScrapingCompletedEvent, ScrapingEventHandler())
event_bus.subscribe(RecognitionStartedEvent, RecognitionEventHandler())
event_bus.subscribe(RecognitionCompletedEvent, RecognitionEventHandler())
