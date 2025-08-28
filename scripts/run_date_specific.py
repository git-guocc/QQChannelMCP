#!/usr/bin/env python3
"""
指定日期数据采集脚本
支持采集指定日期（如 2025-08-27）的QQ频道数据

默认行为：
- 仅采集+下载媒体文件（图片、GIF）
- 不启用AI识别（节省API调用成本）
- 不启用HelloKitty复制功能

使用示例：
# 基本使用（仅采集+下载）
python scripts/run_date_specific.py --date 2025-08-27

# 完整功能（包含AI识别和复制）
python scripts/run_date_specific.py --date 2025-08-27 --recognition --copy
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# 将 src 加入路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from orchestrator.workflow_orchestrator import WorkflowOrchestrator
from core.settings import settings
from collector.enhanced_channel_scraper import EnhancedQQChannelScraper
from utils.directory_manager import DirectoryManager


class DateSpecificDirectoryManager(DirectoryManager):
    """支持指定日期的目录管理器"""
    
    def __init__(self, base_dir: str = "data/dayupdate", target_date: Optional[datetime] = None):
        super().__init__(base_dir)
        self.target_date = target_date or datetime.now()
    
    def get_today_directory(self, posts_count: Optional[int] = None) -> Path:
        """获取指定日期的目录路径"""
        date_str = self.target_date.strftime("%Y-%m-%d")
        target_dir = self.base_dir / date_str
        
        # 创建目录结构
        target_dir.mkdir(exist_ok=True)
        (target_dir / "images").mkdir(exist_ok=True)
        if settings.app.enable_video:
            (target_dir / "videos").mkdir(exist_ok=True)
        (target_dir / "gifs").mkdir(exist_ok=True)
        (target_dir / "unknown").mkdir(exist_ok=True)
        
        return target_dir


class DateSpecificChannelScraper(EnhancedQQChannelScraper):
    """支持指定日期范围的抓取器"""
    
    def __init__(self, config, target_date: Optional[datetime] = None):
        super().__init__(config)
        self.target_date = target_date or datetime.now()
        # 使用自定义的目录管理器
        self.directory_manager = DateSpecificDirectoryManager(
            target_date=self.target_date
        )
    
    def _today_start(self):
        """返回指定日期的开始时间"""
        return datetime(
            self.target_date.year, 
            self.target_date.month, 
            self.target_date.day
        )
    
    def _today_end(self):
        """返回指定日期的结束时间"""
        start = self._today_start()
        return start + timedelta(days=1) - timedelta(microseconds=1)
    
    def _is_target_date_post(self, post_time: datetime) -> bool:
        """判断帖子是否属于目标日期"""
        if not post_time:
            return True  # 未知时间的帖子保留，避免漏抓
        
        start = self._today_start()
        end = self._today_end()
        return start <= post_time <= end


class DateSpecificWorkflowOrchestrator(WorkflowOrchestrator):
    """支持指定日期的工作流编排器"""
    
    def __init__(self, target_date: Optional[datetime] = None):
        super().__init__()
        self.target_date = target_date or datetime.now()
    
    async def execute_complete_workflow(
        self,
        channel_url: str,
        max_posts: int = 200,
        enable_recognition: bool = False,
        enable_copy: bool = False,
    ):
        """执行指定日期的完整工作流"""
        logger = logging.getLogger(__name__)
        
        # 使用自定义的抓取器
        scraper = DateSpecificChannelScraper(
            config=settings, 
            target_date=self.target_date
        )
        
        logger.info(f"开始采集指定日期数据: {self.target_date.strftime('%Y-%m-%d')}")
        
        try:
            # 抓取指定日期的数据
            posts = await scraper.scrape_channel_posts(channel_url, max_posts)
            
            if not posts:
                logger.warning(f"未找到 {self.target_date.strftime('%Y-%m-%d')} 的帖子")
                return {
                    "success": True,
                    "message": f"未找到指定日期 {self.target_date.strftime('%Y-%m-%d')} 的帖子",
                    "posts_count": 0,
                    "target_date": self.target_date.strftime('%Y-%m-%d')
                }
            
            # 使用现有的下载服务，但指向指定日期的目录
            download_result = await self.downloader.download_posts_media(posts)
            
            result = {
                "success": True,
                "message": f"成功采集 {self.target_date.strftime('%Y-%m-%d')} 的数据",
                "target_date": self.target_date.strftime('%Y-%m-%d'),
                "posts_count": len(posts),
                "detailed_results": {
                    "scraping": {"data": {"posts": posts}},
                    "download": download_result
                }
            }
            
            # 可选：AI识别
            if enable_recognition and posts:
                recognition_result = await self.recognition_service.process_images(
                    scraper.directory_manager.get_today_directory() / "images"
                )
                result["detailed_results"]["recognition"] = recognition_result
            
            # 可选：复制HelloKitty图片
            if enable_copy and enable_recognition:
                from services.image_copy_service import ImageCopyService
                copy_service = ImageCopyService(str(scraper.directory_manager.get_today_directory()))
                hellokitty_results = result["detailed_results"].get("recognition", {}).get("data", {}).get("results", [])
                copy_results = copy_service.copy_hellokitty_images(hellokitty_results)
                
                # 构造复制结果
                copy_result = {
                    "success": True,
                    "data": {
                        "copied_files": sum(1 for r in copy_results if r.success),
                        "total_files": len(copy_results),
                        "destination_directory": str(copy_service.destination_directory)
                    }
                }
                result["detailed_results"]["copy"] = copy_result
            
            return result
            
        except Exception as e:
            logger.exception(f"指定日期采集失败: {e}")
            return {
                "success": False,
                "message": f"采集 {self.target_date.strftime('%Y-%m-%d')} 数据失败",
                "error": str(e),
                "target_date": self.target_date.strftime('%Y-%m-%d')
            }


def setup_logging(log_file: Path | None):
    log_level = getattr(logging, settings.logging.level, logging.INFO)
    log_format = settings.logging.format
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)


async def run_date_specific(
    channel_url: str, 
    target_date: str, 
    max_posts: int, 
    enable_recognition: bool, 
    enable_copy: bool
) -> int:
    logger = logging.getLogger(__name__)
    
    try:
        # 解析目标日期
        date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError as e:
        logger.error(f"日期格式错误: {target_date}，请使用 YYYY-MM-DD 格式")
        return 1
    
    # 创建指定日期的工作流编排器
    orchestrator = DateSpecificWorkflowOrchestrator(target_date=date_obj)
    
    logger.info(f"开始采集指定日期: {target_date}, max_posts={max_posts}")
    
    start_time = datetime.now()
    try:
        result = await orchestrator.execute_complete_workflow(
            channel_url=channel_url,
            max_posts=max_posts,
            enable_recognition=enable_recognition,
            enable_copy=enable_copy,
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        if result.get("success"):
            logger.info(
                f"[{target_date}] 采集成功 | 帖子数={result.get('posts_count', 0)} "
                f"耗时={duration:.2f}s"
            )
            
            # 显示下载统计
            download_data = result.get("detailed_results", {}).get("download", {}).get("data", {})
            if download_data:
                logger.info(
                    f"[{target_date}] 下载统计 | 图片={download_data.get('images_count', 0)} "
                    f"GIF={download_data.get('gifs_count', 0)} "
                    f"目录={download_data.get('download_directory', 'N/A')}"
                )
            
            return 0
        else:
            logger.error(f"[{target_date}] 采集失败: {result.get('message')}")
            return 2
            
    except Exception as e:
        logger.exception(f"[{target_date}] 执行异常: {e}")
        return 3


def main():
    if load_dotenv:
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
    
    parser = argparse.ArgumentParser(description="QQChannelMCP 指定日期数据采集")
    parser.add_argument("--channel-url", default="https://pd.qq.com/g/5yy11f95s1", help="频道链接")
    parser.add_argument("--date", required=True, help="目标日期 (YYYY-MM-DD)，如: 2025-08-27")
    parser.add_argument("--max-posts", type=int, default=500, help="最大采集帖子数（建议比日常增量更大）")
    parser.add_argument("--recognition", action="store_true", help="启用AI识别（默认关闭，节省成本）")
    parser.add_argument("--copy", action="store_true", help="启用HelloKitty复制（默认关闭，需配合--recognition使用）")
    parser.add_argument("--log-file", help="日志文件路径")
    
    args = parser.parse_args()
    
    # 设置日志
    log_file = None
    if args.log_file:
        log_file = Path(args.log_file)
    else:
        log_file = PROJECT_ROOT / "logs" / f"date_specific_{args.date.replace('-', '')}.log"
    
    setup_logging(log_file)
    
    # 执行指定日期采集
    exit_code = asyncio.run(
        run_date_specific(
            channel_url=args.channel_url,
            target_date=args.date,
            max_posts=args.max_posts,
            enable_recognition=args.recognition,
            enable_copy=args.copy,
        )
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()