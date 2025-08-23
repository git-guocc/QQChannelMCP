#!/usr/bin/env python3
"""
完整HelloKitty图片下载器 - 基于Chrome方案
使用经过验证的enhanced_channel_scraper获取帖子，然后下载所有图片
"""

import os
import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
import logging

# 导入智能增量管理器
try:
    from .smart_incremental_manager import SmartIncrementalManager
except ImportError:
    from smart_incremental_manager import SmartIncrementalManager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompleteHelloKittyDownloader:
    """完整的HelloKitty图片下载器"""
    
    def __init__(self, download_dir=None):
        if download_dir is None:
            # 使用新的目录管理器
            from src.utils.directory_manager import get_media_subdirectory
            self.download_dir = get_media_subdirectory("images")
        else:
            self.download_dir = Path(download_dir)
        
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # 增量更新管理
        self.post_mapping = {}  # 存储帖子ID到序号的映射
        self.existing_posts = set()  # 已存在的帖子ID集合
        
        # 统计信息
        self.stats = {
            "total_posts": 0,
            "posts_with_images": 0,
            "total_images": 0,
            "downloaded_images": 0,
            "failed_downloads": 0,
            "start_time": time.time()
        }
    
    def filter_24h_posts(self, posts):
        """筛选24小时内的帖子"""
        now = datetime.now()
        filtered_posts = []
        
        for post in posts:
            # 使用post.post_time（datetime对象）或创建相对时间字符串
            time_str = self._get_time_string(post)
            if self._is_within_24h(time_str, now):
                filtered_posts.append(post)
                
        logger.info(f"筛选出24小时内的帖子: {len(filtered_posts)}/{len(filtered_posts)}")
        return filtered_posts
    
    def load_existing_post_mapping(self):
        """加载已存在的帖子映射关系"""
        try:
            # 扫描现有文件，重建帖子映射
            for file_path in self.download_dir.glob("*"):
                if file_path.is_file():
                    filename = file_path.name
                    # 解析文件名获取帖子序号
                    if "_image_" in filename:
                        parts = filename.split("_")
                        if len(parts) >= 3:
                            post_number = parts[0]
                            # 这里可以进一步解析帖子ID，暂时使用文件名作为标识
                            self.post_mapping[filename] = post_number
                            self.existing_posts.add(filename)
            
            logger.info(f"加载了 {len(self.post_mapping)} 个现有帖子的映射关系")
        except Exception as e:
            logger.warning(f"加载现有帖子映射失败: {e}")
    
    def get_post_number_for_update(self, post, total_posts, post_idx):
        """为增量更新获取帖子序号"""
        # 只对有图片的帖子分配序号，确保序号连续
        # 新帖子获得较大编号，旧帖子获得较小编号
        post_number = total_posts - post_idx
        
        # 记录映射关系（用于后续增量更新）
        post_id = getattr(post, 'post_id', None) or f"post_{post_idx}"
        self.post_mapping[post_id] = str(post_number).zfill(3)
        
        return str(post_number).zfill(3)
    
    def _get_time_string(self, post):
        """获取帖子的时间字符串，优先使用相对时间格式"""
        # 如果post.post_time是datetime对象，计算相对时间
        if hasattr(post, 'post_time') and post.post_time:
            try:
                now = datetime.now()
                if post.post_time.tzinfo:
                    # 如果有时区信息，转换为本地时间
                    now = now.replace(tzinfo=post.post_time.tzinfo)
                
                time_diff = now - post.post_time
                
                # 计算相对时间
                total_seconds = int(time_diff.total_seconds())
                if total_seconds < 60:
                    return f"{total_seconds}秒前"
                elif total_seconds < 3600:
                    minutes = total_seconds // 60
                    return f"{minutes}分钟前"
                elif total_seconds < 86400:
                    hours = total_seconds // 3600
                    return f"{hours}小时前"
                else:
                    days = total_seconds // 86400
                    return f"{days}天前"
                    
            except Exception as e:
                logger.warning(f"时间计算失败: {e}")
        
        # 回退到字符串时间
        if hasattr(post, 'post_time_str'):
            return post.post_time_str
        
        # 默认认为是今天的
        return "0小时前"
    
    def _is_within_24h(self, time_str, now):
        """判断帖子是否在24小时内"""
        if not time_str:
            return False
            
        try:
            # 处理相对时间格式
            if "分钟前" in time_str:
                return True
            elif "小时前" in time_str:
                hours = int(time_str.replace("小时前", ""))
                return hours <= 24
            elif "天前" in time_str:
                days = int(time_str.replace("天前", ""))
                return days <= 1
            elif "昨天" in time_str:
                return True
            elif "-" in time_str and len(time_str) <= 6:  # MM-DD格式
                month, day = map(int, time_str.split("-"))
                post_date = datetime(now.year, month, day)
                return (now - post_date).days <= 1
            else:
                # 其他格式暂时认为是今天的
                return True
                
        except Exception as e:
            logger.warning(f"时间解析失败: {time_str}, {e}")
            return False
    
    async def download_image(self, session, image_url, filename, post_title="", max_retries=3):
        """下载单张图片，支持重试机制"""
        for attempt in range(max_retries):
            try:
                # 设置超时和重试
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                async with session.get(image_url, timeout=timeout) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # 验证内容是否为空或过小
                        if len(content) < 100:  # 小于100字节可能是错误页面
                            logger.warning(f"⚠️ 内容过小: {filename}, 大小: {len(content)} bytes")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(1)  # 等待1秒后重试
                                continue
                            else:
                                logger.error(f"❌ 下载失败: {filename}, 内容过小")
                                self.stats["failed_downloads"] += 1
                                return False
                        
                        filepath = self.download_dir / filename
                        
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        
                        logger.info(f"✅ 下载成功: {filename} ({len(content)} bytes)")
                        self.stats["downloaded_images"] += 1
                        return True
                    else:
                        logger.warning(f"❌ 下载失败: {filename}, HTTP {response.status}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2)  # 等待2秒后重试
                            continue
                        else:
                            self.stats["failed_downloads"] += 1
                            return False
                        
            except asyncio.TimeoutError:
                logger.warning(f"⏰ 下载超时: {filename}, 尝试 {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                else:
                    logger.error(f"❌ 下载失败: {filename}, 超时")
                    self.stats["failed_downloads"] += 1
                    return False
                    
            except Exception as e:
                logger.error(f"❌ 下载异常: {filename}, {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    self.stats["failed_downloads"] += 1
                    return False
        
        return False
    
    def _is_valid_image_url(self, url):
        """验证图片URL是否有效"""
        if not url:
            return False
        
        # 检查URL格式
        if not url.startswith(('http://', 'https://')):
            return False
        
        # 检查是否为图片文件
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        url_lower = url.lower()
        
        # 检查文件扩展名
        has_valid_ext = any(url_lower.endswith(ext) for ext in valid_extensions)
        
        # 检查URL是否包含图片相关关键词
        has_image_keywords = any(keyword in url_lower for keyword in ['image', 'img', 'photo', 'pic'])
        
        # 检查URL长度（过长的URL可能有问题）
        if len(url) > 500:
            return False
        
        return has_valid_ext or has_image_keywords
    
    def _sort_posts_by_time(self, posts):
        """按照发帖时间排序帖子（最新在前）"""
        try:
            sorted_posts = sorted(
                posts,
                key=lambda p: p.post_time if hasattr(p, 'post_time') and p.post_time else datetime.min,
                reverse=True  # 最新在前
            )
            
            logger.info(f"帖子排序完成，最新发帖时间: {sorted_posts[0].post_time if sorted_posts and hasattr(sorted_posts[0], 'post_time') and sorted_posts[0].post_time else '未知'}")
            return sorted_posts
            
        except Exception as e:
            logger.warning(f"帖子排序失败: {e}")
            return posts
    
    def generate_filename(self, image_url, post_index, image_index, post_time=None):
        """生成文件名"""
        # 解析文件扩展名
        parsed_url = urlparse(image_url)
        path = parsed_url.path
        ext = Path(path).suffix or '.jpg'
        
        # 生成时间戳
        if post_time and hasattr(post_time, 'strftime'):
            timestamp = post_time.strftime("%Y%m%d_%H%M%S")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 新的文件名格式: 20250823_205541_image_02.jpg
        filename = f"{timestamp}_image_{image_index:02d}{ext}"
        
        return filename
    
    async def download_all_images(self, posts):
        """下载所有图片"""
        self.stats["total_posts"] = len(posts)
        
        # 初始化智能增量管理器
        self.incremental_manager = SmartIncrementalManager(self.download_dir)
        
        # 筛选24小时内的帖子
        recent_posts = self.filter_24h_posts(posts)
        
        if not recent_posts:
            logger.warning("没有找到24小时内的帖子")
            return
        
        # 收集所有图片URL
        download_tasks = []
        image_count = 0
        
        async with aiohttp.ClientSession() as session:
            # 统计新帖子数量并记录时间
            new_posts_count = 0
            new_posts = []
            existing_posts_with_images = []
            
            for post in recent_posts:
                if hasattr(post, 'images') and post.images:
                    if self.incremental_manager.is_duplicate_post(post):
                        logger.info(f"跳过重复帖子: {post.title or '无标题'}")
                        # 这是已经存在的有图片的帖子，需要收集起来
                        existing_posts_with_images.append(post)
                        continue
                    
                    # 记录帖子的发帖时间到增量管理器
                    if hasattr(post, 'post_time') and post.post_time:
                        self.incremental_manager.record_post_time(post, post.post_time)
                    
                    new_posts.append(post)
                    new_posts_count += 1
            
            # 简化逻辑：直接处理所有新帖子，不需要序号
            posts_with_images = new_posts + existing_posts_with_images
            self.stats["posts_with_images"] = len(posts_with_images)
            
            if new_posts_count > 0:
                logger.info(f"发现 {new_posts_count} 个新帖子，开始下载...")
            
            # 现在为所有帖子生成文件名
            for post in posts_with_images:
                

                
                for img_idx, image_url in enumerate(post.images):
                        if image_url and self._is_valid_image_url(image_url):  # 确保URL不为空且有效
                            image_count += 1
                            filename = self.generate_filename(image_url, None, img_idx + 1, post.post_time)
                            
                            # 创建下载任务
                            task = self.download_image(session, image_url, filename, post.title or "")
                            download_tasks.append(task)
                        elif image_url:
                            logger.warning(f"⚠️ 跳过无效图片URL: {image_url}")
                            self.stats["failed_downloads"] += 1
            
            self.stats["total_images"] = image_count
            logger.info(f"开始下载 {image_count} 张图片...")
            
            # 并发下载所有图片
            if download_tasks:
                results = await asyncio.gather(*download_tasks, return_exceptions=True)
                
                # 统计下载结果
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"下载任务异常: {result}")
                        self.stats["failed_downloads"] += 1
                    elif result is False:
                        self.stats["failed_downloads"] += 1
                    # True 的情况已经在 download_image 中统计了
                
                # 保存重复检测记录
                self.incremental_manager.save_mapping()
                

    

    
    def print_statistics(self):
        """打印统计信息"""
        elapsed_time = time.time() - self.stats["start_time"]
        
        print("\n" + "="*50)
        print("📊 下载统计报告")
        print("="*50)
        print(f"📝 总帖子数: {self.stats['total_posts']}")
        print(f"🖼️  含图帖子数: {self.stats['posts_with_images']}")
        print(f"🎯 总图片数: {self.stats['total_images']}")
        print(f"✅ 成功下载: {self.stats['downloaded_images']}")
        print(f"❌ 下载失败: {self.stats['failed_downloads']}")
        print(f"⏱️  耗时: {elapsed_time:.2f} 秒")
        print(f"📁 保存目录: {self.download_dir.absolute()}")
        
        if self.stats["total_images"] > 0:
            success_rate = (self.stats["downloaded_images"] / self.stats["total_images"]) * 100
            print(f"🎉 成功率: {success_rate:.1f}%")
        
        print("="*50)
        
        # 显示增量管理器状态
        if hasattr(self, 'incremental_manager'):
            self.incremental_manager.print_mapping_summary()

async def main():
    """主函数"""
    print("🎀 启动HelloKitty图片下载器...")
    
    # 导入并使用enhanced_channel_scraper
    try:
        from collector.enhanced_channel_scraper import EnhancedQQChannelScraper
        from core.config import QQChannelConfig
        
        # 初始化配置和scraper
        config = QQChannelConfig()
        scraper = EnhancedQQChannelScraper(config)
        
        # HelloKitty频道URL
        channel_url = "https://pd.qq.com/g/5yy11f95s1"
        
        print(f"🔍 开始抓取HelloKitty频道: {channel_url}")
        
        # 抓取帖子
        posts = await scraper.scrape_channel_posts(channel_url)
        
        if not posts:
            print("❌ 没有抓取到任何帖子")
            return
            
        print(f"✅ 成功抓取到 {len(posts)} 个帖子")
        
        # 初始化下载器
        downloader = CompleteHelloKittyDownloader()
        
        # 下载所有图片
        await downloader.download_all_images(posts)
        
        # 显示统计信息
        downloader.print_statistics()
        
        # 检查下载目录
        downloaded_files = list(downloader.download_dir.glob("*"))
        if downloaded_files:
            print(f"\n📂 下载的文件:")
            for i, file in enumerate(downloaded_files[:10], 1):  # 只显示前10个
                size_kb = file.stat().st_size / 1024
                print(f"   {i:2d}. {file.name} ({size_kb:.1f} KB)")
            
            if len(downloaded_files) > 10:
                print(f"   ... 还有 {len(downloaded_files) - 10} 个文件")
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保enhanced_channel_scraper.py已正确创建")
    except Exception as e:
        logger.error(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())