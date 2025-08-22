"""
QQ频道数据采集MCP服务器
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastmcp import FastMCP

from ..core.config import QQChannelConfig
from ..core.exceptions import format_error_message
from ..collector.channel_scraper import QQChannelScraper
from ..collector.filter_engine import FilterEngine
from ..collector.image_downloader import ImageDownloader
from ..models.filter_criteria import FilterCriteria, QuickFilters
from ..storage.json_storage import JSONStorage
from ..storage.csv_storage import CSVStorage
from ..storage.image_storage import ImageStorage

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建MCP应用
app = FastMCP("QQ频道数据采集工具")

# 全局配置和组件
config = QQChannelConfig()
scraper = QQChannelScraper(config)
filter_engine = FilterEngine()
image_downloader = ImageDownloader(config)


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
        result = await scraper.test_connection(channel_url)
        return result
        
    except Exception as e:
        logger.error(f"连接测试失败: {e}")
        return {
            "success": False,
            "error": format_error_message(e)
        }


@app.tool()
async def collect_channel_posts(
    channel_url: str,
    max_posts: int = 50,
    time_range_days: Optional[int] = None,
    keywords: Optional[List[str]] = None,
    min_likes: Optional[int] = None,
    min_comments: Optional[int] = None,
    post_types: Optional[List[str]] = None,
    has_images: Optional[bool] = None,
    authors: Optional[List[str]] = None,
    save_images: bool = True,
    output_format: str = "json",
    sort_by: str = "time",
    sort_order: str = "desc"
) -> Dict[str, Any]:
    """
    采集QQ频道帖子数据
    
    Args:
        channel_url: 频道链接
        max_posts: 最大采集数量
        time_range_days: 采集最近几天的内容
        keywords: 关键词筛选列表
        min_likes: 最小点赞数
        min_comments: 最小评论数
        post_types: 帖子类型筛选 ['text', 'image', 'video']
        has_images: 是否必须包含图片
        authors: 指定作者列表
        save_images: 是否下载图片
        output_format: 输出格式 ('json' 或 'csv')
        sort_by: 排序字段 ('time', 'likes', 'comments')
        sort_order: 排序顺序 ('asc', 'desc')
    
    Returns:
        采集结果统计
    """
    try:
        logger.info(f"开始采集频道: {channel_url}")
        
        # 1. 采集原始数据
        raw_posts = await scraper.scrape_channel_posts(channel_url, max_posts)
        
        if not raw_posts:
            return {
                "success": True,
                "message": "未找到任何帖子",
                "total_collected": 0,
                "after_filter": 0
            }
        
        # 2. 构建筛选条件
        criteria = FilterCriteria(
            time_range_days=time_range_days,
            keywords=keywords or [],
            min_likes=min_likes,
            min_comments=min_comments,
            post_types=post_types or [],
            has_images=has_images,
            author_filter=authors or [],
            sort_by=sort_by,
            sort_order=sort_order,
            max_results=max_posts
        )
        
        # 3. 筛选帖子
        filtered_posts = await filter_engine.filter_posts(raw_posts, criteria)
        
        # 4. 下载图片（如果需要）
        downloaded_images = 0
        if save_images and filtered_posts:
            downloaded_images = await _download_posts_images(filtered_posts)
        
        # 5. 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format.lower() == "csv":
            storage = CSVStorage(f"data/qq_channel_posts_{timestamp}.csv")
            await storage.save_posts(filtered_posts, use_chinese_headers=True)
            output_file = f"data/qq_channel_posts_{timestamp}.csv"
        else:
            storage = JSONStorage(f"data/qq_channel_posts_{timestamp}.json")
            metadata = {
                "channel_url": channel_url,
                "filter_criteria": criteria.to_dict(),
                "collection_time": datetime.now().isoformat()
            }
            await storage.save_posts(filtered_posts, metadata)
            output_file = f"data/qq_channel_posts_{timestamp}.json"
        
        # 6. 获取筛选统计
        filter_stats = filter_engine.get_filter_statistics(raw_posts, filtered_posts, criteria)
        
        return {
            "success": True,
            "total_collected": len(raw_posts),
            "after_filter": len(filtered_posts),
            "filter_rate": filter_stats["filter_rate"],
            "criteria_summary": criteria.get_summary(),
            "images_downloaded": downloaded_images,
            "output_file": output_file,
            "output_format": output_format,
            "filter_statistics": filter_stats["filter_effects"],
            "message": f"成功采集 {len(filtered_posts)} 个帖子"
        }
        
    except Exception as e:
        logger.error(f"采集频道帖子失败: {e}")
        return {
            "success": False,
            "error": format_error_message(e)
        }


@app.tool()
async def quick_collect_hot_posts(
    channel_url: str,
    days: int = 7,
    min_likes: int = 50,
    max_posts: int = 30,
    save_images: bool = True
) -> Dict[str, Any]:
    """
    快速采集热门帖子
    
    Args:
        channel_url: 频道链接
        days: 最近几天
        min_likes: 最小点赞数
        max_posts: 最大采集数量
        save_images: 是否下载图片
    
    Returns:
        采集结果
    """
    try:
        # 使用预设的热门帖子筛选条件
        criteria = QuickFilters.recent_hot_posts(days, min_likes)
        criteria.max_results = max_posts
        
        # 调用主采集函数
        return await collect_channel_posts(
            channel_url=channel_url,
            max_posts=max_posts * 2,  # 采集更多数据用于筛选
            time_range_days=days,
            min_likes=min_likes,
            save_images=save_images,
            sort_by="likes",
            sort_order="desc"
        )
        
    except Exception as e:
        logger.error(f"快速采集热门帖子失败: {e}")
        return {
            "success": False,
            "error": format_error_message(e)
        }


@app.tool()
async def search_posts_by_keywords(
    channel_url: str,
    keywords: List[str],
    days: int = 14,
    max_posts: int = 50,
    min_likes: int = 0
) -> Dict[str, Any]:
    """
    根据关键词搜索帖子
    
    Args:
        channel_url: 频道链接
        keywords: 关键词列表
        days: 搜索最近几天
        max_posts: 最大结果数量
        min_likes: 最小点赞数
    
    Returns:
        搜索结果
    """
    try:
        logger.info(f"关键词搜索: {keywords}")
        
        return await collect_channel_posts(
            channel_url=channel_url,
            max_posts=max_posts * 3,  # 采集更多数据用于关键词匹配
            time_range_days=days,
            keywords=keywords,
            min_likes=min_likes,
            sort_by="likes",
            sort_order="desc"
        )
        
    except Exception as e:
        logger.error(f"关键词搜索失败: {e}")
        return {
            "success": False,
            "error": format_error_message(e)
        }


@app.tool()
async def collect_author_posts(
    channel_url: str,
    author_name: str,
    days: int = 30,
    max_posts: int = 50
) -> Dict[str, Any]:
    """
    采集指定作者的帖子
    
    Args:
        channel_url: 频道链接
        author_name: 作者昵称
        days: 最近几天
        max_posts: 最大数量
    
    Returns:
        采集结果
    """
    try:
        logger.info(f"采集作者帖子: {author_name}")
        
        return await collect_channel_posts(
            channel_url=channel_url,
            max_posts=max_posts * 2,
            time_range_days=days,
            authors=[author_name],
            sort_by="time",
            sort_order="desc"
        )
        
    except Exception as e:
        logger.error(f"采集作者帖子失败: {e}")
        return {
            "success": False,
            "error": format_error_message(e)
        }


@app.tool()
async def analyze_collected_data(
    data_file: str = None,
    analysis_type: str = "summary"
) -> Dict[str, Any]:
    """
    分析已采集的数据
    
    Args:
        data_file: 数据文件路径，不指定则使用最新的
        analysis_type: 分析类型 ('summary', 'trends', 'authors', 'content')
    
    Returns:
        分析结果
    """
    try:
        # 如果没有指定文件，寻找最新的数据文件
        if not data_file:
            import glob
            json_files = glob.glob("data/qq_channel_posts_*.json")
            if not json_files:
                return {
                    "success": False,
                    "error": "未找到数据文件"
                }
            data_file = max(json_files)  # 选择最新的文件
        
        # 加载数据
        storage = JSONStorage(data_file)
        posts = await storage.load_posts()
        
        if not posts:
            return {
                "success": False,
                "error": "数据文件为空"
            }
        
        # 根据分析类型返回不同的分析结果
        if analysis_type == "summary":
            return _analyze_summary(posts)
        elif analysis_type == "trends":
            return _analyze_trends(posts)
        elif analysis_type == "authors":
            return _analyze_authors(posts)
        elif analysis_type == "content":
            return _analyze_content(posts)
        else:
            return {
                "success": False,
                "error": f"不支持的分析类型: {analysis_type}"
            }
        
    except Exception as e:
        logger.error(f"数据分析失败: {e}")
        return {
            "success": False,
            "error": format_error_message(e)
        }


@app.tool()
async def export_data(
    input_file: str = None,
    output_format: str = "csv",
    include_images: bool = False
) -> Dict[str, Any]:
    """
    导出数据到不同格式
    
    Args:
        input_file: 输入文件路径
        output_format: 输出格式 ('csv', 'excel', 'json')
        include_images: 是否包含图片信息
    
    Returns:
        导出结果
    """
    try:
        # 寻找数据文件
        if not input_file:
            import glob
            json_files = glob.glob("data/qq_channel_posts_*.json")
            if not json_files:
                return {
                    "success": False,
                    "error": "未找到数据文件"
                }
            input_file = max(json_files)
        
        # 加载数据
        storage = JSONStorage(input_file)
        posts = await storage.load_posts()
        
        if not posts:
            return {
                "success": False,
                "error": "数据文件为空"
            }
        
        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format.lower() == "csv":
            output_file = f"data/export_{timestamp}.csv"
            csv_storage = CSVStorage(output_file)
            await csv_storage.save_posts(posts, use_chinese_headers=True)
        
        elif output_format.lower() == "excel":
            output_file = f"data/export_{timestamp}.xlsx"
            # 这里可以添加Excel导出逻辑
            return {
                "success": False,
                "error": "Excel导出功能暂未实现"
            }
        
        else:
            output_file = f"data/export_{timestamp}.json"
            await storage.export_to_format(output_file, "json")
        
        return {
            "success": True,
            "input_file": input_file,
            "output_file": output_file,
            "output_format": output_format,
            "total_records": len(posts),
            "message": f"成功导出 {len(posts)} 条记录"
        }
        
    except Exception as e:
        logger.error(f"数据导出失败: {e}")
        return {
            "success": False,
            "error": format_error_message(e)
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
        
        json_info = []
        for file_path in json_files:
            storage = JSONStorage(file_path)
            info = storage.get_storage_info()
            json_info.append(info)
        
        csv_info = []
        for file_path in csv_files:
            storage = CSVStorage(file_path)
            info = storage.get_storage_statistics()
            csv_info.append(info)
        
        # 图片存储信息
        image_storage = ImageStorage()
        image_info = image_storage.get_storage_statistics()
        
        # 总体统计
        total_size = sum(info.get('size_bytes', 0) for info in json_info + csv_info)
        total_records = sum(info.get('record_count', 0) for info in json_info + csv_info)
        
        return {
            "success": True,
            "json_files": json_info,
            "csv_files": csv_info,
            "image_storage": image_info,
            "summary": {
                "total_files": len(json_files) + len(csv_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "total_records": total_records,
                "data_directory": "data/"
            }
        }
        
    except Exception as e:
        logger.error(f"获取存储信息失败: {e}")
        return {
            "success": False,
            "error": format_error_message(e)
        }


async def _download_posts_images(posts) -> int:
    """下载帖子中的图片"""
    total_images = 0
    
    try:
        async with image_downloader:
            for post in posts:
                if post.images:
                    # 下载图片
                    results = await image_downloader.download_images(
                        post.images, 
                        f"post_{post.post_id}"
                    )
                    
                    # 更新本地路径
                    local_paths = [r['local_path'] for r in results if r['success']]
                    post.image_paths = local_paths
                    
                    # 注册到图片存储
                    image_storage = ImageStorage()
                    for result in results:
                        if result['success']:
                            await image_storage.register_image(
                                local_path=result['local_path'],
                                original_url=result['url'],
                                post_id=post.post_id
                            )
                    
                    total_images += len([r for r in results if r['success']])
    
    except Exception as e:
        logger.error(f"下载图片失败: {e}")
    
    return total_images


def _analyze_summary(posts) -> Dict[str, Any]:
    """生成数据摘要分析"""
    total_posts = len(posts)
    total_likes = sum(post.like_count for post in posts)
    total_comments = sum(post.comment_count for post in posts)
    
    # 按类型统计
    type_counts = {}
    for post in posts:
        type_counts[post.post_type] = type_counts.get(post.post_type, 0) + 1
    
    # 按作者统计
    author_counts = {}
    for post in posts:
        author_counts[post.author_name] = author_counts.get(post.author_name, 0) + 1
    
    top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # 时间分析
    if posts and posts[0].post_time:
        times = [p.post_time for p in posts if p.post_time]
        time_range = {
            "earliest": min(times).isoformat(),
            "latest": max(times).isoformat()
        } if times else {}
    else:
        time_range = {}
    
    return {
        "success": True,
        "analysis_type": "summary",
        "data": {
            "total_posts": total_posts,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "avg_likes_per_post": round(total_likes / total_posts, 2) if total_posts > 0 else 0,
            "avg_comments_per_post": round(total_comments / total_posts, 2) if total_posts > 0 else 0,
            "post_types": type_counts,
            "unique_authors": len(author_counts),
            "top_authors": top_authors,
            "time_range": time_range,
            "posts_with_images": len([p for p in posts if p.has_images()])
        }
    }


def _analyze_trends(posts) -> Dict[str, Any]:
    """分析趋势数据"""
    # 这里可以实现更复杂的趋势分析
    # 比如按时间分组统计、互动趋势等
    return {
        "success": True,
        "analysis_type": "trends",
        "message": "趋势分析功能开发中"
    }


def _analyze_authors(posts) -> Dict[str, Any]:
    """分析作者数据"""
    author_stats = {}
    
    for post in posts:
        author = post.author_name
        if author not in author_stats:
            author_stats[author] = {
                "posts_count": 0,
                "total_likes": 0,
                "total_comments": 0,
                "posts_with_images": 0
            }
        
        stats = author_stats[author]
        stats["posts_count"] += 1
        stats["total_likes"] += post.like_count
        stats["total_comments"] += post.comment_count
        if post.has_images():
            stats["posts_with_images"] += 1
    
    # 计算平均值
    for author, stats in author_stats.items():
        posts_count = stats["posts_count"]
        stats["avg_likes"] = round(stats["total_likes"] / posts_count, 2)
        stats["avg_comments"] = round(stats["total_comments"] / posts_count, 2)
        stats["image_rate"] = round(stats["posts_with_images"] / posts_count, 2)
    
    # 排序
    top_by_posts = sorted(author_stats.items(), key=lambda x: x[1]["posts_count"], reverse=True)[:10]
    top_by_likes = sorted(author_stats.items(), key=lambda x: x[1]["total_likes"], reverse=True)[:10]
    
    return {
        "success": True,
        "analysis_type": "authors",
        "data": {
            "total_authors": len(author_stats),
            "top_by_posts": [(author, stats) for author, stats in top_by_posts],
            "top_by_likes": [(author, stats) for author, stats in top_by_likes],
            "author_stats": author_stats
        }
    }


def _analyze_content(posts) -> Dict[str, Any]:
    """分析内容数据"""
    content_lengths = [len(post.content) for post in posts]
    
    # 内容长度统计
    length_stats = {
        "min_length": min(content_lengths) if content_lengths else 0,
        "max_length": max(content_lengths) if content_lengths else 0,
        "avg_length": round(sum(content_lengths) / len(content_lengths), 2) if content_lengths else 0
    }
    
    # 关键词频率（简单实现）
    from collections import Counter
    all_content = " ".join(post.content for post in posts)
    words = all_content.split()
    word_freq = Counter(words).most_common(20)
    
    return {
        "success": True,
        "analysis_type": "content",
        "data": {
            "length_stats": length_stats,
            "top_words": word_freq,
            "total_characters": sum(content_lengths)
        }
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # 标准输入输出模式，用于MCP
        app.run_stdio()
    else:
        # 开发模式
        print("QQ频道数据采集MCP服务器")
        print("使用 --stdio 参数启动MCP模式")
        print("可用工具:")
        for tool_name in app.list_tools():
            print(f"  - {tool_name}")
