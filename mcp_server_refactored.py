#!/usr/bin/env python3
"""
重构后的QQ频道数据采集MCP服务器
使用新的工作流编排器架构，提供更好的模块化和可维护性
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastmcp import FastMCP

from core.settings import settings
from core.results import ResultBuilder, ResultType
from orchestrator.workflow_orchestrator import WorkflowOrchestrator

# 设置日志
logging.basicConfig(
    level=getattr(logging, settings.logging.level),
    format=settings.logging.format
)
logger = logging.getLogger(__name__)

# 创建MCP应用
app = FastMCP("QQ频道数据采集工具 - 重构版")

# 全局工作流编排器
orchestrator = WorkflowOrchestrator()

@app.tool()
async def download_only(
    channel_url: str = "https://pd.qq.com/g/5yy11f95s1",
    max_posts: int = None
) -> Dict[str, Any]:
    """
    采集+下载（不识别、不复制）

    Args:
        channel_url: 频道链接
        max_posts: 最大采集帖子数

    Returns:
        下载阶段结果（包含目录与manifest等）
    """
    try:
        # 默认从 settings 读取最大帖子数
        if max_posts is None:
            max_posts = settings.scraping.max_posts
        result = await orchestrator.execute_complete_workflow(
            channel_url=channel_url,
            max_posts=max_posts,
            enable_recognition=False,
            enable_copy=False
        )
        return result
    except Exception as e:
        logger.error(f"download_only 执行失败: {e}")
        return {
            "success": False,
            "message": "download_only 执行失败",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.tool()
async def full_pipeline(
    channel_url: str = "https://pd.qq.com/g/5yy11f95s1",
    max_posts: int = None
) -> Dict[str, Any]:
    """
    采集+下载+识别+复制（一步到位）

    Args:
        channel_url: 频道链接
        max_posts: 最大采集帖子数

    Returns:
        完整工作流执行结果
    """
    try:
        # 默认从 settings 读取最大帖子数
        if max_posts is None:
            max_posts = settings.scraping.max_posts
        result = await orchestrator.execute_complete_workflow(
            channel_url=channel_url,
            max_posts=max_posts,
            enable_recognition=True,
            enable_copy=True
        )
        return result
    except Exception as e:
        logger.error(f"full_pipeline 执行失败: {e}")
        return {
            "success": False,
            "message": "full_pipeline 执行失败",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.tool()
async def get_configuration_summary() -> Dict[str, Any]:
    """
    获取配置摘要
    
    Returns:
        当前配置摘要
    """
    try:
        settings.print_summary()
        return {
            "success": True,
            "message": "配置摘要获取成功",
            "data": settings.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取配置摘要失败: {e}")
        return {
            "success": False,
            "message": "获取配置摘要失败",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.tool()
async def test_connection(channel_url: str) -> Dict[str, Any]:
    """
    测试QQ频道连接
    
    Args:
        channel_url: 频道链接
        
    Returns:
        连接测试结果
    """
    try:
        logger.info(f"测试连接: {channel_url}")
        
        # 使用工作流编排器测试连接
        result = await orchestrator.scraper.test_connection(channel_url)
        
        return {
            "success": True,
            "message": "连接测试成功",
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"连接测试失败: {e}")
        return {
            "success": False,
            "message": "连接测试失败",
            "error": str(e),
            "details": {
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            },
            "timestamp": datetime.now().isoformat()
        }


@app.tool()
async def execute_complete_workflow(
    channel_url: str = "https://pd.qq.com/g/5yy11f95s1",
    max_posts: int = None,
    enable_recognition: bool = True,
    enable_copy: bool = True
) -> Dict[str, Any]:
    """
    执行完整工作流：采集 -> 下载 -> 识别 -> 复制
    
    Args:
        channel_url: 频道链接 (默认HelloKitty频道)
        max_posts: 最大采集帖子数
        enable_recognition: 是否启用图片识别
        enable_copy: 是否启用图片复制
        
    Returns:
        完整工作流执行结果
    """
    try:
        logger.info(f"开始执行完整工作流: {channel_url}")
        
        # 使用工作流编排器执行完整流程
        result = await orchestrator.execute_complete_workflow(
            channel_url=channel_url,
            max_posts=max_posts,
            enable_recognition=enable_recognition,
            enable_copy=enable_copy
        )
        
        return result
        
    except Exception as e:
        logger.error(f"工作流执行失败: {e}")
        return {
            "success": False,
            "message": "工作流执行失败",
            "error": str(e),
            "details": {
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            },
            "timestamp": datetime.now().isoformat()
        }


@app.tool()
async def execute_scraping_only(
    channel_url: str = "https://pd.qq.com/g/5yy11f95s1",
    max_posts: int = None
) -> Dict[str, Any]:
    """
    仅执行数据采集阶段
    
    Args:
        channel_url: 频道链接
        max_posts: 最大采集帖子数
        
    Returns:
        数据采集结果
    """
    try:
        logger.info(f"开始执行数据采集: {channel_url}")
        
        # 执行采集阶段
        result = await orchestrator._execute_scraping_phase(
            channel_url, 
            max_posts or settings.scraping.max_posts
        )
        
        return {
            "success": result.is_success(),
            "message": result.message,
            "data": result.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"数据采集失败: {e}")
        return {
            "success": False,
            "message": "数据采集失败",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.tool()
async def execute_recognition_only(
    image_directory: str,
    ai_provider: str = None
) -> Dict[str, Any]:
    """
    仅执行图片识别阶段
    
    Args:
        image_directory: 图片目录路径
        ai_provider: AI提供商 (可选)
        
    Returns:
        图片识别结果
    """
    try:
        logger.info(f"开始执行图片识别: {image_directory}")
        
        # 创建识别服务
        if ai_provider:
            from core.ai_client import AIProvider
            provider_enum = AIProvider(ai_provider)
            recognition_service = HelloKittyRecognitionService(preferred_provider=provider_enum)
        else:
            recognition_service = orchestrator.recognition_service
        
        # 执行识别
        recognition_results = await recognition_service.recognize_directory(image_directory)
        
        # 统计结果
        total_images = len(recognition_results)
        hellokitty_images = sum(1 for r in recognition_results if r.is_hellokitty)
        failed_images = sum(1 for r in recognition_results if r is None)
        
        result = {
            "success": True,
            "message": "图片识别完成",
            "data": {
                "total_images": total_images,
                "hellokitty_images": hellokitty_images,
                "failed_images": failed_images,
                "recognition_results": [
                    {
                        "image_path": r.image_path,
                        "is_hellokitty": r.is_hellokitty,
                        "confidence": r.confidence,
                        "ai_response": r.ai_response,
                        "provider": r.provider
                    } for r in recognition_results if r
                ]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # 打印统计信息
        recognition_service.print_statistics()
        
        return result
        
    except Exception as e:
        logger.error(f"图片识别失败: {e}")
        return {
            "success": False,
            "message": "图片识别失败",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.tool()
async def execute_copy_only(
    source_directory: str,
    destination_directory: str = None
) -> Dict[str, Any]:
    """
    仅执行图片复制阶段
    
    Args:
        source_directory: 源图片目录
        destination_directory: 目标目录 (可选)
        
    Returns:
        图片复制结果
    """
    try:
        logger.info(f"开始执行图片复制: {source_directory}")
        
        # 创建复制服务
        copy_service = ImageCopyService(source_directory, destination_directory)
        
        # 查找所有图片文件
        from pathlib import Path
        image_files = list(Path(source_directory).glob("*_image_*.jpg"))
        
        if not image_files:
            return {
                "success": False,
                "message": "未找到图片文件",
                "data": {"source_directory": source_directory},
                "timestamp": datetime.now().isoformat()
            }
        
        # 创建模拟识别结果（假设所有图片都是HelloKitty）
        from services.hellokitty_recognition_service import RecognitionResult
        mock_results = [
            RecognitionResult(
                image_path=str(img_file),
                is_hellokitty=True,
                confidence=1.0,
                ai_response="是",
                provider="manual",
                processing_time=0.0,
                file_size=img_file.stat().st_size,
                original_format="jpg"
            ) for img_file in image_files
        ]
        
        # 执行复制
        copy_results = copy_service.copy_hellokitty_images(mock_results)
        
        # 统计结果
        total_files = len(copy_results)
        copied_files = sum(1 for r in copy_results if r.success)
        failed_copies = total_files - copied_files
        total_size = sum(r.file_size for r in copy_results if r.success)
        
        result = {
            "success": True,
            "message": "图片复制完成",
            "data": {
                "total_files": total_files,
                "copied_files": copied_files,
                "failed_copies": failed_copies,
                "total_size": total_size,
                "source_directory": source_directory,
                "destination_directory": str(copy_service.destination_directory)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # 打印统计信息
        copy_service.print_statistics()
        
        return result
        
    except Exception as e:
        logger.error(f"图片复制失败: {e}")
        return {
            "success": False,
            "message": "图片复制失败",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.tool()
async def get_workflow_performance_stats() -> Dict[str, Any]:
    """
    获取工作流性能统计
    
    Returns:
        工作流性能统计信息
    """
    try:
        stats = orchestrator.get_performance_stats()
        
        return {
            "success": True,
            "message": "性能统计获取成功",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取性能统计失败: {e}")
        return {
            "success": False,
            "message": "获取性能统计失败",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.tool()
async def get_storage_info() -> Dict[str, Any]:
    """
    获取存储信息
    
    Returns:
        存储统计信息
    """
    try:
        import glob
        from pathlib import Path
        
        # 统计JSON文件
        json_files = glob.glob("data/qq_channel_posts_*.json")
        csv_files = glob.glob("data/qq_channel_posts_*.csv")
        
        # 多媒体存储信息（使用新规范：data/dayupdate/YYYY-MM-DD）
        dayupdate_dir = Path(settings.storage.base_directory) / "dayupdate"
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")

        day_dir = dayupdate_dir / date_str
        media_stats = {"images": 0, "gifs": 0, "videos": 0}
        manifest_data = None
        if day_dir.exists():
            for media_type in media_stats.keys():
                media_path = day_dir / media_type
                if media_path.exists():
                    media_stats[media_type] = len(list(media_path.glob("*")))
            # 读取 manifest.json
            manifest_path = day_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    import json
                    manifest_data = json.loads(manifest_path.read_text(encoding='utf-8'))
                except Exception:
                    manifest_data = None

        total_media = sum(media_stats.values())

        return {
            "success": True,
            "message": "存储信息获取成功",
            "data": {
                "json_files_count": len(json_files),
                "csv_files_count": len(csv_files),
                "media_files": media_stats,
                "total_media_files": total_media,
                "storage_base_directory": settings.storage.base_directory,
                "current_date": date_str,
                "day_directory": str(day_dir),
                "manifest": manifest_data
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取存储信息失败: {e}")
        return {
            "success": False,
            "message": "获取存储信息失败",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.tool()
async def validate_ai_services() -> Dict[str, Any]:
    """
    验证AI服务状态
    
    Returns:
        AI服务状态信息
    """
    try:
        from core.ai_client import AIClientManager, AIProvider
        
        # 创建AI客户端管理器
        ai_manager = AIClientManager(settings, AIProvider(settings.ai.preferred_provider))
        
        # 测试所有客户端
        test_results = await ai_manager.test_all_clients()
        
        return {
            "success": True,
            "message": "AI服务状态验证完成",
            "data": {
                "preferred_provider": settings.ai.preferred_provider,
                "test_results": test_results,
                "provider_status": ai_manager.get_provider_status()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI服务验证失败: {e}")
        return {
            "success": False,
            "message": "AI服务验证失败",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # 启动时打印配置摘要
    settings.print_summary()
    
    # 启动MCP服务器
    app.run()
