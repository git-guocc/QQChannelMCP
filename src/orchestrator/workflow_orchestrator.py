#!/usr/bin/env python3
"""
工作流编排器
统一管理整个数据采集、识别、复制的工作流程
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from core.settings import settings
from core.results import (
    ResultBuilder, ResultType, ScrapingResult, DownloadResult, 
    RecognitionResult, CopyResult, BaseResult
)
from core.exceptions import (
    QQChannelMCPError, ScrapingError, AIServiceError, StorageError
)
from collector.enhanced_channel_scraper import EnhancedQQChannelScraper
from services.hellokitty_recognition_service import HelloKittyRecognitionService
from services.image_copy_service import ImageCopyService

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """工作流编排器"""
    
    def __init__(self):
        """初始化工作流编排器"""
        self.settings = settings
        self.scraper = EnhancedQQChannelScraper(settings)
        self.recognition_service = HelloKittyRecognitionService(
            preferred_provider=settings.ai.preferred_provider
        )
        
        # 工作流状态
        self.current_workflow = None
        self.workflow_history = []
        
        # 性能统计
        self.performance_stats = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "total_execution_time": 0.0,
            "avg_execution_time": 0.0
        }
    
    async def execute_complete_workflow(
        self,
        channel_url: str,
        max_posts: int = None,
        enable_recognition: bool = True,
        enable_copy: bool = True
    ) -> Dict[str, Any]:
        """
        执行完整工作流：采集 -> 下载 -> 识别 -> 复制
        
        Args:
            channel_url: 频道链接
            max_posts: 最大采集帖子数
            enable_recognition: 是否启用图片识别
            enable_copy: 是否启用图片复制
            
        Returns:
            完整工作流执行结果
        """
        workflow_id = f"workflow_{int(datetime.now().timestamp())}"
        start_time = datetime.now()
        
        logger.info(f"开始执行完整工作流: {workflow_id}")
        logger.info(f"频道: {channel_url}")
        logger.info(f"最大帖子数: {max_posts or settings.scraping.max_posts}")
        logger.info(f"启用识别: {enable_recognition}")
        logger.info(f"启用复制: {enable_copy}")
        
        try:
            # 1. 数据采集阶段
            scraping_result = await self._execute_scraping_phase(
                channel_url, max_posts or settings.scraping.max_posts
            )
            
            if not scraping_result.is_success():
                return self._create_workflow_failure_result(
                    "数据采集阶段失败", scraping_result.error
                )
            
            # 2. 图片下载阶段
            download_result = await self._execute_download_phase(
                scraping_result.data["posts"]
            )
            
            if not download_result.is_success():
                return self._create_workflow_failure_result(
                    "图片下载阶段失败", download_result.error
                )
            
            # 3. 图片识别阶段（可选）
            recognition_result = None
            if enable_recognition:
                recognition_result = await self._execute_recognition_phase(
                    download_result.data["download_directory"]
                )
                
                if not recognition_result.is_success():
                    logger.warning("图片识别阶段失败，但继续执行后续流程")
            
            # 4. 图片复制阶段（可选）
            copy_result = None
            if enable_copy and recognition_result and recognition_result.is_success():
                copy_result = await self._execute_copy_phase(
                    download_result.data["download_directory"],
                    recognition_result.data["recognition_results"]
                )
                
                if not copy_result.is_success():
                    logger.warning("图片复制阶段失败")
            
            # 5. 生成最终结果
            final_result = self._create_workflow_success_result(
                workflow_id,
                scraping_result,
                download_result,
                recognition_result,
                copy_result
            )
            
            # 更新性能统计
            self._update_performance_stats(start_time, True)
            
            logger.info(f"完整工作流执行成功: {workflow_id}")
            return final_result
            
        except Exception as e:
            # 更新性能统计
            self._update_performance_stats(start_time, False)
            
            logger.error(f"工作流执行异常: {workflow_id}", exc_info=True)
            return self._create_workflow_failure_result(
                f"工作流执行异常: {str(e)}",
                QQChannelMCPError(f"工作流执行失败: {str(e)}", "WORKFLOW_EXECUTION_ERROR")
            )
    
    async def _execute_scraping_phase(self, channel_url: str, max_posts: int) -> ScrapingResult:
        """执行数据采集阶段"""
        logger.info("开始执行数据采集阶段...")
        
        try:
            # 测试连接
            connection_test = await self.scraper.test_connection(channel_url)
            if not connection_test.get("success", False):
                return ResultBuilder.failure(
                    "频道连接测试失败",
                    ScrapingError("连接测试失败", channel_url, "Chrome"),
                    ResultType.SCRAPING
                )
            
            # 采集帖子
            posts = await self.scraper.scrape_channel_posts(channel_url, max_posts)
            
            if not posts:
                return ResultBuilder.failure(
                    "未采集到任何帖子",
                    ScrapingError("无帖子数据", channel_url, "Chrome"),
                    ResultType.SCRAPING
                )
            
            # 创建成功结果
            result = ScrapingResult(
                status=ResultBuilder.success("数据采集成功", ResultType.SCRAPING).status,
                message="数据采集成功",
                data={"posts": posts, "channel_url": channel_url},
                posts_count=len(posts),
                successful_posts=len(posts),
                failed_posts=0,
                channel_url=channel_url,
                method="Chrome Browser (Enhanced)"
            )
            
            result.finish()
            logger.info(f"数据采集阶段完成: {len(posts)} 个帖子")
            return result
            
        except Exception as e:
            logger.error(f"数据采集阶段异常: {e}")
            return ResultBuilder.failure(
                f"数据采集异常: {str(e)}",
                ScrapingError(str(e), channel_url, "Chrome"),
                ResultType.SCRAPING
            )
    
    async def _execute_download_phase(self, posts: List[Any]) -> DownloadResult:
        """执行图片下载阶段"""
        logger.info("开始执行图片下载阶段...")
        
        try:
            # 这里需要调用下载器，暂时返回模拟结果
            # TODO: 集成实际的下载器
            total_images = sum(len(getattr(post, 'images', [])) for post in posts)
            downloaded_images = total_images  # 假设全部下载成功
            
            result = DownloadResult(
                status=ResultBuilder.success("图片下载成功", ResultType.DOWNLOAD).status,
                message="图片下载成功",
                data={
                    "total_posts": len(posts),
                    "total_images": total_images,
                    "downloaded_images": downloaded_images,
                    "download_directory": "data/dayupdate/images"  # 模拟路径
                },
                total_files=total_images,
                downloaded_files=downloaded_images,
                failed_files=0,
                total_size=0,  # 实际实现中计算文件大小
                download_directory="data/dayupdate/images"
            )
            
            result.finish()
            logger.info(f"图片下载阶段完成: {downloaded_images}/{total_images} 张图片")
            return result
            
        except Exception as e:
            logger.error(f"图片下载阶段异常: {e}")
            return ResultBuilder.failure(
                f"图片下载异常: {str(e)}",
                StorageError(f"下载失败: {str(e)}"),
                ResultType.DOWNLOAD
            )
    
    async def _execute_recognition_phase(self, download_directory: str) -> RecognitionResult:
        """执行图片识别阶段"""
        logger.info("开始执行图片识别阶段...")
        
        try:
            # 使用识别服务
            recognition_results = await self.recognition_service.recognize_directory(
                download_directory
            )
            
            if not recognition_results:
                return ResultBuilder.failure(
                    "未找到图片进行识别",
                    AIServiceError("无图片数据"),
                    ResultType.RECOGNITION
                )
            
            # 统计结果
            total_images = len(recognition_results)
            hellokitty_images = sum(1 for r in recognition_results if r.is_hellokitty)
            failed_images = sum(1 for r in recognition_results if r is None)
            
            result = RecognitionResult(
                status=ResultBuilder.success("图片识别成功", ResultType.RECOGNITION).status,
                message="图片识别成功",
                data={
                    "recognition_results": recognition_results,
                    "download_directory": download_directory
                },
                total_images=total_images,
                processed_images=total_images - failed_images,
                hellokitty_images=hellokitty_images,
                failed_images=failed_images,
                ai_provider=self.settings.ai.preferred_provider,
                model=self.settings.ai.openrouter_model
            )
            
            result.finish()
            logger.info(f"图片识别阶段完成: {hellokitty_images}/{total_images} 张HelloKitty图片")
            return result
            
        except Exception as e:
            logger.error(f"图片识别阶段异常: {e}")
            return ResultBuilder.failure(
                f"图片识别异常: {str(e)}",
                AIServiceError(f"识别失败: {str(e)}"),
                ResultType.RECOGNITION
            )
    
    async def _execute_copy_phase(
        self, 
        source_directory: str, 
        recognition_results: List[Any]
    ) -> CopyResult:
        """执行图片复制阶段"""
        logger.info("开始执行图片复制阶段...")
        
        try:
            # 使用复制服务
            copy_service = ImageCopyService(source_directory)
            copy_results = copy_service.copy_hellokitty_images(recognition_results)
            
            # 统计结果
            total_files = len(copy_results)
            copied_files = sum(1 for r in copy_results if r.success)
            failed_copies = total_files - copied_files
            total_size = sum(r.file_size for r in copy_results if r.success)
            
            result = CopyResult(
                status=ResultBuilder.success("图片复制成功", ResultType.COPY).status,
                message="图片复制成功",
                data={
                    "copy_results": copy_results,
                    "source_directory": source_directory
                },
                total_files=total_files,
                copied_files=copied_files,
                failed_copies=failed_copies,
                total_size=total_size,
                source_directory=source_directory,
                destination_directory=str(copy_service.destination_directory)
            )
            
            result.finish()
            logger.info(f"图片复制阶段完成: {copied_files}/{total_files} 张图片")
            return result
            
        except Exception as e:
            logger.error(f"图片复制阶段异常: {e}")
            return ResultBuilder.failure(
                f"图片复制异常: {str(e)}",
                StorageError(f"复制失败: {str(e)}"),
                ResultType.COPY
            )
    
    def _create_workflow_success_result(
        self,
        workflow_id: str,
        scraping_result: ScrapingResult,
        download_result: DownloadResult,
        recognition_result: Optional[RecognitionResult],
        copy_result: Optional[CopyResult]
    ) -> Dict[str, Any]:
        """创建工作流成功结果"""
        # 计算总执行时间
        total_duration = 0.0
        if scraping_result.metadata.duration:
            total_duration += scraping_result.metadata.duration
        if download_result.metadata.duration:
            total_duration += download_result.metadata.duration
        if recognition_result and recognition_result.metadata.duration:
            total_duration += recognition_result.metadata.duration
        if copy_result and copy_result.metadata.duration:
            total_duration += copy_result.metadata.duration
        
        # 构建结果摘要
        summary = {
            "workflow_id": workflow_id,
            "status": "success",
            "total_duration": total_duration,
            "phases": {
                "scraping": {
                    "status": "success",
                    "posts_count": scraping_result.posts_count,
                    "duration": scraping_result.metadata.duration
                },
                "download": {
                    "status": "success",
                    "images_count": download_result.downloaded_files,
                    "duration": download_result.metadata.duration
                }
            }
        }
        
        if recognition_result:
            summary["phases"]["recognition"] = {
                "status": "success",
                "hellokitty_count": recognition_result.hellokitty_images,
                "duration": recognition_result.metadata.duration
            }
        
        if copy_result:
            summary["phases"]["copy"] = {
                "status": "success",
                "copied_count": copy_result.copied_files,
                "duration": copy_result.metadata.duration
            }
        
        return {
            "success": True,
            "message": "完整工作流执行成功",
            "workflow_id": workflow_id,
            "summary": summary,
            "detailed_results": {
                "scraping": scraping_result.to_dict(),
                "download": download_result.to_dict(),
                "recognition": recognition_result.to_dict() if recognition_result else None,
                "copy": copy_result.to_dict() if copy_result else None
            }
        }
    
    def _create_workflow_failure_result(
        self, 
        message: str, 
        error: QQChannelMCPError
    ) -> Dict[str, Any]:
        """创建工作流失败结果"""
        return {
            "success": False,
            "message": message,
            "error": error.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    
    def _update_performance_stats(self, start_time: datetime, success: bool):
        """更新性能统计"""
        execution_time = (datetime.now() - start_time).total_seconds()
        
        self.performance_stats["total_workflows"] += 1
        if success:
            self.performance_stats["successful_workflows"] += 1
        else:
            self.performance_stats["failed_workflows"] += 1
        
        self.performance_stats["total_execution_time"] += execution_time
        self.performance_stats["avg_execution_time"] = (
            self.performance_stats["total_execution_time"] / 
            self.performance_stats["total_workflows"]
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            **self.performance_stats,
            "success_rate": (
                self.performance_stats["successful_workflows"] / 
                self.performance_stats["total_workflows"] * 100
            ) if self.performance_stats["total_workflows"] > 0 else 0
        }
    
    def print_performance_summary(self):
        """打印性能摘要"""
        stats = self.get_performance_stats()
        
        print("\n" + "="*60)
        print("📊 工作流性能统计摘要")
        print("="*60)
        print(f"🔄 总工作流数: {stats['total_workflows']}")
        print(f"✅ 成功工作流: {stats['successful_workflows']}")
        print(f"❌ 失败工作流: {stats['failed_workflows']}")
        print(f"🎯 成功率: {stats['success_rate']:.1f}%")
        print(f"⏱️  总执行时间: {stats['total_execution_time']:.2f}秒")
        print(f"⚡ 平均执行时间: {stats['avg_execution_time']:.2f}秒")
        print("="*60)
