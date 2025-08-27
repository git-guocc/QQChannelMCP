#!/usr/bin/env python3
"""
统一结果返回
标准化所有操作的返回格式，提供一致的数据结构
"""

import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .exceptions import QQChannelMCPError


class ResultStatus(Enum):
    """结果状态枚举"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ResultType(Enum):
    """结果类型枚举"""
    SCRAPING = "scraping"
    DOWNLOAD = "download"
    RECOGNITION = "recognition"
    COPY = "copy"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    SYSTEM = "system"


@dataclass
class ResultMetadata:
    """结果元数据"""
    operation_id: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    retry_count: int = 0
    source: str = ""
    version: str = "1.0.0"
    
    def __post_init__(self):
        if self.end_time and self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
    
    def finish(self):
        """标记操作完成"""
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "operation_id": self.operation_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "retry_count": self.retry_count,
            "source": self.source,
            "version": self.version
        }


@dataclass
class BaseResult:
    """基础结果类"""
    status: ResultStatus
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[QQChannelMCPError] = None
    metadata: ResultMetadata = field(default_factory=ResultMetadata)
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = ResultMetadata()
    
    def add_warning(self, warning: str):
        """添加警告信息"""
        self.warnings.append(warning)
    
    def set_error(self, error: QQChannelMCPError):
        """设置错误信息"""
        self.error = error
        self.status = ResultStatus.FAILED
    
    def finish(self):
        """标记操作完成"""
        self.metadata.finish()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "status": self.status.value,
            "message": self.message,
            "metadata": self.metadata.to_dict(),
            "warnings": self.warnings
        }
        
        if self.data:
            result["data"] = self.data
        
        if self.error:
            result["error"] = self.error.to_dict()
        
        return result
    
    def is_success(self) -> bool:
        """检查是否成功"""
        return self.status in [ResultStatus.SUCCESS, ResultStatus.PARTIAL_SUCCESS]
    
    def is_failed(self) -> bool:
        """检查是否失败"""
        return self.status == ResultStatus.FAILED


@dataclass
class ScrapingResult(BaseResult):
    """数据采集结果"""
    posts_count: int = 0
    successful_posts: int = 0
    failed_posts: int = 0
    channel_url: str = ""
    method: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.metadata.source = "scraping"
        self.metadata.operation_id = f"scraping_{int(time.time())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "posts_count": self.posts_count,
            "successful_posts": self.successful_posts,
            "failed_posts": self.failed_posts,
            "channel_url": self.channel_url,
            "method": self.method
        })
        return base_dict


@dataclass
class DownloadResult(BaseResult):
    """下载结果"""
    total_files: int = 0
    downloaded_files: int = 0
    failed_files: int = 0
    total_size: int = 0
    download_directory: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.metadata.source = "download"
        self.metadata.operation_id = f"download_{int(time.time())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "total_files": self.total_files,
            "downloaded_files": self.downloaded_files,
            "failed_files": self.failed_files,
            "total_size": self.total_size,
            "download_directory": self.download_directory
        })
        return base_dict


@dataclass
class RecognitionResult(BaseResult):
    """识别结果"""
    total_images: int = 0
    processed_images: int = 0
    hellokitty_images: int = 0
    failed_images: int = 0
    ai_provider: str = ""
    model: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.metadata.source = "recognition"
        self.metadata.operation_id = f"recognition_{int(time.time())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "total_images": self.total_images,
            "processed_images": self.processed_images,
            "hellokitty_images": self.hellokitty_images,
            "failed_images": self.failed_images,
            "ai_provider": self.ai_provider,
            "model": self.model
        })
        return base_dict


@dataclass
class CopyResult(BaseResult):
    """复制结果"""
    total_files: int = 0
    copied_files: int = 0
    failed_copies: int = 0
    total_size: int = 0
    source_directory: str = ""
    destination_directory: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.metadata.source = "copy"
        self.metadata.operation_id = f"copy_{int(time.time())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "total_files": self.total_files,
            "copied_files": self.copied_files,
            "failed_copies": self.failed_copies,
            "total_size": self.total_size,
            "source_directory": self.source_directory,
            "destination_directory": self.destination_directory
        })
        return base_dict


@dataclass
class ValidationResult(BaseResult):
    """验证结果"""
    total_items: int = 0
    valid_items: int = 0
    invalid_items: int = 0
    validation_rules: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        self.metadata.source = "validation"
        self.metadata.operation_id = f"validation_{int(time.time())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "total_items": self.total_items,
            "valid_items": self.valid_items,
            "invalid_items": self.invalid_items,
            "validation_rules": self.validation_rules
        })
        return base_dict


class ResultBuilder:
    """结果构建器"""
    
    @staticmethod
    def success(
        message: str,
        data: Optional[Dict[str, Any]] = None,
        result_type: ResultType = ResultType.SYSTEM
    ) -> BaseResult:
        """创建成功结果"""
        result = BaseResult(
            status=ResultStatus.SUCCESS,
            message=message,
            data=data
        )
        result.metadata.source = result_type.value
        return result
    
    @staticmethod
    def partial_success(
        message: str,
        data: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[str]] = None,
        result_type: ResultType = ResultType.SYSTEM
    ) -> BaseResult:
        """创建部分成功结果"""
        result = BaseResult(
            status=ResultStatus.PARTIAL_SUCCESS,
            message=message,
            data=data,
            warnings=warnings or []
        )
        result.metadata.source = result_type.value
        return result
    
    @staticmethod
    def failure(
        message: str,
        error: Optional[QQChannelMCPError] = None,
        result_type: ResultType = ResultType.SYSTEM
    ) -> BaseResult:
        """创建失败结果"""
        result = BaseResult(
            status=ResultStatus.FAILED,
            message=message,
            error=error
        )
        result.metadata.source = result_type.value
        return result
    
    @staticmethod
    def timeout(
        message: str = "操作超时",
        result_type: ResultType = ResultType.SYSTEM
    ) -> BaseResult:
        """创建超时结果"""
        result = BaseResult(
            status=ResultStatus.TIMEOUT,
            message=message
        )
        result.metadata.source = result_type.value
        return result


def format_result_for_mcp(result: Union[BaseResult, Dict[str, Any]]) -> Dict[str, Any]:
    """格式化结果为统一的 MCP 输出结构

    入参支持两类：
    - BaseResult 及其子类：阶段性结果（采集/下载/识别/复制）
    - dict：完整工作流结果（`WorkflowOrchestrator.execute_complete_workflow` 返回值）

    统一输出字段（可能部分为空）：
    - success: 是否成功（bool）
    - status: 字符串状态（success/failed/partial_success 等）
    - message: 结果信息
    - timestamp: 开始时间（ISO8601）。工作流结果优先使用顶层 timestamp
    - duration: 总时长（工作流取 summary.total_duration；阶段结果取 metadata.duration）
    - data: 附加数据（工作流包含 workflow_id、summary、detailed_results）
    - error: 错误对象（如存在）
    - warnings: 警告列表（阶段结果如存在）
    """
    # 1) 处理阶段性结果对象
    if isinstance(result, BaseResult):
        mcp_result = {
            "success": result.is_success(),
            "message": result.message,
            "timestamp": result.metadata.start_time.isoformat(),
            "duration": result.metadata.duration,
            "status": result.status.value,
        }

        if result.data:
            mcp_result["data"] = result.data

        if result.error:
            mcp_result["error"] = {
                "type": result.error.__class__.__name__,
                "code": result.error.error_code,
                "message": result.error.message,
                "details": result.error.details,
            }

        if result.warnings:
            mcp_result["warnings"] = result.warnings

        return mcp_result

    # 2) 处理完整工作流 dict 结果
    if isinstance(result, dict):
        success = bool(result.get("success", False))
        message = result.get("message", "")
        # timestamp: 优先使用顶层；否则从各阶段最早开始时间推断；再退化为当前时间
        timestamp = result.get("timestamp")
        if not timestamp:
            detailed = result.get("detailed_results") or {}
            start_times: List[str] = []
            try:
                for phase in ("scraping", "download", "recognition", "copy"):
                    phase_obj = detailed.get(phase)
                    if isinstance(phase_obj, dict):
                        meta = phase_obj.get("metadata") or {}
                        st = meta.get("start_time")
                        if isinstance(st, str):
                            start_times.append(st)
                if start_times:
                    # 采用最早的开始时间
                    timestamp = min(start_times)
            except Exception:
                # 容错：保持为空，后续用当前时间
                pass

        duration = None
        try:
            duration = (result.get("summary") or {}).get("total_duration")
        except Exception:
            duration = None

        mcp_result = {
            "success": success,
            "message": message,
            "timestamp": timestamp or datetime.now().isoformat(),
            "duration": duration,
            "status": "success" if success else "failed",
        }

        data: Dict[str, Any] = {}
        if "workflow_id" in result:
            data["workflow_id"] = result["workflow_id"]
        if "summary" in result:
            data["summary"] = result["summary"]
        if "detailed_results" in result:
            data["detailed_results"] = result["detailed_results"]
        if data:
            mcp_result["data"] = data

        # 透传错误
        if isinstance(result.get("error"), dict):
            mcp_result["error"] = result["error"]

        return mcp_result

    # 3) 不支持的类型，回退为失败结果
    return {
        "success": False,
        "message": "不支持的结果类型，无法格式化",
        "timestamp": datetime.now().isoformat(),
        "status": "failed",
    }
