"""
异常处理模块
"""

from typing import Optional, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class QQChannelError(Exception):
    """QQ频道工具基础异常类"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class ScrapingError(QQChannelError):
    """数据采集异常"""
    pass


class ParsingError(QQChannelError):
    """数据解析异常"""
    pass


class StorageError(QQChannelError):
    """数据存储异常"""
    pass


class NetworkError(QQChannelError):
    """网络请求异常"""
    pass


class ConfigError(QQChannelError):
    """配置异常"""
    pass


class FilterError(QQChannelError):
    """筛选异常"""
    pass


def handle_exception(func):
    """异常处理装饰器"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except QQChannelError:
            # 重新抛出已知异常
            raise
        except Exception as e:
            # 包装未知异常
            logger.error(f"未处理的异常在 {func.__name__}: {e}")
            raise QQChannelError(f"执行 {func.__name__} 时发生未知错误: {str(e)}")
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except QQChannelError:
            # 重新抛出已知异常
            raise
        except Exception as e:
            # 包装未知异常
            logger.error(f"未处理的异常在 {func.__name__}: {e}")
            raise QQChannelError(f"执行 {func.__name__} 时发生未知错误: {str(e)}")
    
    # 根据函数是否为协程选择装饰器
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def format_error_message(error: Exception) -> str:
    """格式化错误消息"""
    if isinstance(error, QQChannelError):
        return f"[{error.error_code or 'ERROR'}] {error.message}"
    else:
        return f"[UNKNOWN] {str(error)}"
