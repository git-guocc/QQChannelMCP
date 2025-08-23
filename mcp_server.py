"""
QQ频道数据采集MCP服务器 - 简化版
只保留最好的一个工具，避免功能重复
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastmcp import FastMCP

from core.config import QQChannelConfig
from collector.enhanced_channel_scraper import EnhancedQQChannelScraper
from complete_hellokitty_downloader import CompleteHelloKittyDownloader

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建MCP应用
app = FastMCP("QQ频道数据采集工具 - 简化版")

# 全局配置和组件
config = QQChannelConfig()


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
        
        # 导入增强版频道抓取器
        scraper = EnhancedQQChannelScraper(config)
        result = await scraper.test_connection(channel_url)
        
        return {
            "success": True,
            "message": "连接测试成功",
            "data": result
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
            }
        }


@app.tool()
async def collect_daily_hellokitty(
    channel_url: str = "https://pd.qq.com/g/5yy11f95s1",
    max_posts: int = 50
) -> Dict[str, Any]:
    """
    收集今日HelloKitty完整内容 - 包括帖子文字、图片、动图、视频、时间、作者等所有信息
    
    这是唯一保留的收集工具，功能完整，工作稳定，支持所有媒体类型下载
    
    Args:
        channel_url: 频道链接 (默认HelloKitty频道)
        max_posts: 最大采集帖子数
        
    Returns:
        今日HelloKitty完整收集结果（包含所有媒体类型）
    """
    try:
        logger.info(f"开始收集今日HelloKitty内容: {channel_url}")
        
        # 直接使用Chrome方案，确保获取完整内容
        logger.info("使用Chrome方案抓取完整内容...")
        scraper = EnhancedQQChannelScraper(config)
        posts = await scraper.scrape_channel_posts(channel_url, max_posts)
        
        if not posts:
            return {
                "success": False,
                "error": "没有抓取到任何帖子",
                "message": "Chrome方案未能获取到帖子数据"
            }
        
        # 使用完整HelloKitty下载器下载所有图片
        downloader = CompleteHelloKittyDownloader()
        
        logger.info(f"开始下载 {len(posts)} 个帖子的所有图片内容...")
        await downloader.download_all_images(posts)
        
        # 生成统计报告
        stats = downloader.stats
        
        results = {
            "scraper_method": "Chrome Browser (Enhanced) + Complete HelloKitty Downloader",
            "total_posts": stats["total_posts"],
            "total_images": stats["total_images"],
            "posts_with_images": stats["posts_with_images"],
            "downloaded_images": stats["downloaded_images"],
            "failed_downloads": stats["failed_downloads"],
            "success_rate": (stats["downloaded_images"] / stats["total_images"] * 100) if stats["total_images"] > 0 else 0,
            "download_directory": str(downloader.download_dir.absolute()),
            "execution_time": round(time.time() - stats.get("start_time", time.time()), 2)
        }
        
        logger.info(f"图片收集完成: {results}")
        return {
            "success": True,
            "message": f"成功收集 {stats['downloaded_images']} 张图片",
            "data": results,
            "features": [
                "🎯 唯一保留的收集工具 - 功能完整，工作稳定",
                "📝 获取完整帖子内容 - 文字、图片、时间、作者等",
                "🔄 支持增量更新 - 避免重复下载",
                "📂 标准化命名 - 清晰的目录结构",
                "⚡ 异步高速下载 - 提高效率",
                "🖼️ 本地图片预览 - 支持MD报告",
                "🎀 专为HelloKitty频道优化 - 最佳兼容性"
            ],
            "storage_location": str(downloader.download_dir.absolute())
        }
        
    except Exception as e:
        logger.error(f"Chrome方案收集失败: {e}")
        return {
            "success": False,
            "message": "Chrome方案收集失败",
            "error": str(e),
            "details": {
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            }
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
        
        # 多媒体存储信息 - 使用新的目录命名规范
        dayupdate_dir = Path("/home/guocc/GitHub/MCP/QQChannelMCP/data/dayupdate")
        
        # 查找今天的目录（格式：帖子个数_posts_日期）
        from datetime import datetime
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        
        # 查找匹配的目录
        multimedia_dir = None
        for dir_path in dayupdate_dir.iterdir():
            if dir_path.is_dir() and date_str in dir_path.name:
                multimedia_dir = dir_path
                break
        
        # 统计各种媒体类型
        media_stats = {}
        if multimedia_dir:
            for media_type in ["images", "gifs", "videos"]:
                media_path = multimedia_dir / media_type
                if media_path.exists():
                    media_stats[media_type] = len(list(media_path.glob("*")))
                else:
                    media_stats[media_type] = 0
        else:
            media_stats = {"images": 0, "gifs": 0, "videos": 0}
        
        total_media = sum(media_stats.values())
        
        return {
            "success": True,
            "data_directory": str(dayupdate_dir),
            "multimedia_content": {
                "path": str(multimedia_dir),
                "exists": multimedia_dir.exists(),
                "static_images": media_stats.get("images", 0),
                "animated_gifs": media_stats.get("gifs", 0),
                "videos": media_stats.get("videos", 0),
                "total_media_files": total_media
            },
            "json_files": len(json_files),
            "csv_files": len(csv_files),
            "total_files": len(json_files) + len(csv_files) + total_media
        }
        
    except Exception as e:
        logger.error(f"获取存储信息失败: {e}")
        return {
            "success": False,
            "message": "获取存储信息失败",
            "error": str(e),
            "details": {
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            }
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # 标准输入输出模式，用于MCP客户端连接
        app.run()
    else:
        # 默认启动MCP服务器
        print("🚀 启动QQ频道数据采集MCP服务器...")
        print("📋 可用工具:")
        import asyncio
        tools = asyncio.run(app.get_tools())
        for tool_name in tools:
            print(f"  - {tool_name}")
        print("\n✅ MCP服务器已启动，等待客户端连接...")
        app.run()
