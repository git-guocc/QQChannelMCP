#!/usr/bin/env python3
"""
统一异常处理
定义所有可能的异常类型，提供统一的错误处理机制
"""

from typing import Optional, Dict, Any, Union
from datetime import datetime


class QQChannelMCPError(Exception):
    """QQChannelMCP基础异常类"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }
    
    def __str__(self):
        return f"{self.__class__.__name__}: {self.message} (Code: {self.error_code})"


class ConfigurationError(QQChannelMCPError):
    """配置错误"""
    
    def __init__(self, message: str, config_key: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)
        self.config_key = config_key


class AIServiceError(QQChannelMCPError):
    """AI服务错误"""
    
    def __init__(self, message: str, provider: str = None, model: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "AI_SERVICE_ERROR", details)
        self.provider = provider
        self.model = model


class AIServiceQuotaExceededError(AIServiceError):
    """AI服务配额超限错误"""
    
    def __init__(self, provider: str, model: str, retry_after: Optional[int] = None):
        message = f"AI服务配额超限: {provider}/{model}"
        details = {"retry_after": retry_after}
        super().__init__(message, provider, model, details)
        self.retry_after = retry_after


class AIServiceConnectionError(AIServiceError):
    """AI服务连接错误"""
    
    def __init__(self, provider: str, model: str, original_error: Exception = None):
        message = f"AI服务连接失败: {provider}/{model}"
        details = {"original_error": str(original_error) if original_error else None}
        super().__init__(message, provider, model, details)
        self.original_error = original_error


class ScrapingError(QQChannelMCPError):
    """数据采集错误"""
    
    def __init__(self, message: str, channel_url: str = None, method: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "SCRAPING_ERROR", details)
        self.channel_url = channel_url
        self.method = method


class ScrapingConnectionError(ScrapingError):
    """采集连接错误"""
    
    def __init__(self, channel_url: str, method: str, original_error: Exception = None):
        message = f"无法连接到频道: {channel_url}"
        details = {"method": method, "original_error": str(original_error) if original_error else None}
        super().__init__(message, channel_url, method, details)
        self.original_error = original_error


class ScrapingTimeoutError(ScrapingError):
    """采集超时错误"""
    
    def __init__(self, channel_url: str, method: str, timeout: Union[int, float]):
        message = f"采集超时: {channel_url} (超时时间: {timeout}s)"
        details = {"method": method, "timeout": timeout}
        super().__init__(message, channel_url, method, details)
        self.timeout = timeout


class StorageError(QQChannelMCPError):
    """存储错误"""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "STORAGE_ERROR", details)
        self.file_path = file_path
        self.operation = operation


class FileNotFoundError(StorageError):
    """文件未找到错误"""
    
    def __init__(self, file_path: str, operation: str = "read"):
        message = f"文件未找到: {file_path}"
        details = {"operation": operation}
        super().__init__(message, file_path, operation, details)


class FilePermissionError(StorageError):
    """文件权限错误"""
    
    def __init__(self, file_path: str, operation: str, original_error: Exception = None):
        message = f"文件权限不足: {file_path} (操作: {operation})"
        details = {"operation": operation, "original_error": str(original_error) if original_error else None}
        super().__init__(message, file_path, operation, details)
        self.original_error = original_error


class FileSizeExceededError(StorageError):
    """文件大小超限错误"""
    
    def __init__(self, file_path: str, file_size: int, max_size: int):
        message = f"文件大小超限: {file_path} ({file_size} > {max_size})"
        details = {"file_size": file_size, "max_size": max_size}
        super().__init__(message, file_path, "size_check", details)
        self.file_size = file_size
        self.max_size = max_size


class ImageProcessingError(QQChannelMCPError):
    """图片处理错误"""
    
    def __init__(self, message: str, image_path: str = None, operation: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "IMAGE_PROCESSING_ERROR", details)
        self.image_path = image_path
        self.operation = operation


class UnsupportedImageFormatError(ImageProcessingError):
    """不支持的图片格式错误"""
    
    def __init__(self, image_path: str, format_name: str, supported_formats: list):
        message = f"不支持的图片格式: {format_name} (支持格式: {', '.join(supported_formats)})"
        details = {"format": format_name, "supported_formats": supported_formats}
        super().__init__(message, image_path, "format_check", details)
        self.format_name = format_name
        self.supported_formats = supported_formats


class ImageConversionError(ImageProcessingError):
    """图片转换错误"""
    
    def __init__(self, image_path: str, source_format: str, target_format: str, original_error: Exception = None):
        message = f"图片格式转换失败: {source_format} -> {target_format}"
        details = {
            "source_format": source_format,
            "target_format": target_format,
            "original_error": str(original_error) if original_error else None
        }
        super().__init__(message, image_path, "conversion", details)
        self.source_format = source_format
        self.target_format = target_format
        self.original_error = original_error


class ValidationError(QQChannelMCPError):
    """数据验证错误"""
    
    def __init__(self, message: str, field_name: str = None, value: Any = None, details: Dict[str, Any] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field_name = field_name
        self.value = value


class TimeFilterError(QQChannelMCPError):
    """时间筛选错误"""
    
    def __init__(self, message: str, time_value: str = None, filter_type: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "TIME_FILTER_ERROR", details)
        self.time_value = time_value
        self.filter_type = filter_type


class NetworkError(QQChannelMCPError):
    """网络错误"""
    
    def __init__(self, message: str, url: str = None, status_code: int = None, details: Dict[str, Any] = None):
        super().__init__(message, "NETWORK_ERROR", details)
        self.url = url
        self.status_code = status_code


class RateLimitError(NetworkError):
    """速率限制错误"""
    
    def __init__(self, url: str, retry_after: Optional[int] = None, details: Dict[str, Any] = None):
        message = f"请求频率超限: {url}"
        details = {"retry_after": retry_after, **details} if details else {"retry_after": retry_after}
        super().__init__(message, url, 429, details)
        self.retry_after = retry_after


def handle_exception(func):
    """异常处理装饰器"""
    import functools
    import logging
    import asyncio
    
    logger = logging.getLogger(__name__)
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except QQChannelMCPError as e:
            logger.error(f"捕获到已知异常: {e}")
            raise
        except Exception as e:
            logger.error(f"捕获到未知异常: {e}", exc_info=True)
            # 转换为通用异常
            raise QQChannelMCPError(
                message=f"操作失败: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                details={"original_error": str(e), "error_type": type(e).__name__}
            )
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except QQChannelMCPError as e:
            logger.error(f"捕获到已知异常: {e}")
            raise
        except Exception as e:
            logger.error(f"捕获到未知异常: {e}", exc_info=True)
            # 转换为通用异常
            raise QQChannelMCPError(
                message=f"操作失败: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                details={"original_error": str(e), "error_type": type(e).__name__}
            )
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def format_error_message(error: Exception) -> str:
    """格式化错误消息"""
    if isinstance(error, QQChannelMCPError):
        return f"[{error.error_code or 'ERROR'}] {error.message}"
    else:
        return f"[UNKNOWN] {str(error)}"
