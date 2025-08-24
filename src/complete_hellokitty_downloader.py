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
    
    def filter_today_posts(self, posts):
        """筛选今天的所有帖子 - 从今天0点到明天0点"""
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        tomorrow_start = today_start + timedelta(days=1)
        
        filtered_posts = []
        
        for post in posts:
            # 只使用真实时间进行逻辑处理
            if hasattr(post, 'post_time') and post.post_time:
                post_time = post.post_time
                # 如果有时区信息，转换为本地时间
                if post_time.tzinfo:
                    post_time = post_time.replace(tzinfo=None)
                
                # 判断是否在今天范围内
                if today_start <= post_time < tomorrow_start:
                    filtered_posts.append(post)
                    logger.debug(f"帖子 '{post.title}' 通过今天筛选: {post_time} (相对时间: {getattr(post, 'post_time_str', '未知')})")
                else:
                    logger.debug(f"帖子 '{post.title}' 被今天筛选过滤: {post_time} (相对时间: {getattr(post, 'post_time_str', '未知')})")
            else:
                logger.warning(f"帖子 '{post.title}' 缺少真实时间信息，无法进行时间筛选")
                
        logger.info(f"筛选出今天的帖子: {len(filtered_posts)}/{len(posts)} (时间范围: {today_start} - {tomorrow_start})")
        return filtered_posts
    
    def filter_recent_hours_posts(self, posts, hours=24):
        """筛选最近N小时内的帖子 - 相对时间窗口"""
        now = datetime.now()
        time_boundary = now - timedelta(hours=hours)
        
        filtered_posts = []
        
        for post in posts:
            # 只使用真实时间进行逻辑处理
            if hasattr(post, 'post_time') and post.post_time:
                post_time = post.post_time
                # 如果有时区信息，转换为本地时间
                if post_time.tzinfo:
                    post_time = post_time.replace(tzinfo=None)
                
                # 判断是否在时间窗口内
                if time_boundary <= post_time <= now:
                    filtered_posts.append(post)
                    logger.debug(f"帖子 '{post.title}' 通过{hours}小时筛选: {post_time} (相对时间: {getattr(post, 'post_time_str', '未知')})")
                else:
                    logger.debug(f"帖子 '{post.title}' 被{hours}小时筛选过滤: {post_time} (相对时间: {getattr(post, 'post_time_str', '未知')})")
            else:
                logger.warning(f"帖子 '{post.title}' 缺少真实时间信息，无法进行时间筛选")
                
        logger.info(f"筛选出最近{hours}小时内的帖子: {len(filtered_posts)}/{len(filtered_posts)} (时间范围: {time_boundary} - {now})")
        return filtered_posts
    
    def filter_24h_posts(self, posts):
        """筛选帖子 - 默认使用今天的所有帖子"""
        return self.filter_today_posts(posts)
    
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
        """判断帖子是否在今天 - 使用绝对日期判断"""
        try:
            # 获取今天的0点时间
            today_start = datetime(now.year, now.month, now.day)
            # 获取明天的0点时间
            tomorrow_start = today_start + timedelta(days=1)
            
            # 直接使用帖子的真实时间判断
            if hasattr(self, 'current_post') and hasattr(self.current_post, 'post_time') and self.current_post.post_time:
                post_time = self.current_post.post_time
                # 如果有时区信息，转换为本地时间
                if post_time.tzinfo:
                    post_time = post_time.replace(tzinfo=None)
                
                # 判断是否在今天范围内：>= 今天0点 且 < 明天0点
                return today_start <= post_time < tomorrow_start
                
            # 如果没有真实时间，返回False（保守处理）
            return False
                
        except Exception as e:
            logger.warning(f"时间判断失败: {e}")
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
                
                # 筛选HelloKitty图片并复制到HelloKitty文件夹
                await self._filter_and_copy_hellokitty_images()
                

    

    
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
    
    async def _filter_and_copy_hellokitty_images(self):
        """筛选HelloKitty图片并复制到HelloKitty文件夹"""
        try:
            logger.info("开始筛选HelloKitty图片...")
            
            # 获取所有下载的图片
            image_files = list(self.download_dir.glob("*_image_*.jpg"))
            if not image_files:
                logger.info("没有找到需要筛选的图片")
                return
            
            logger.info(f"找到 {len(image_files)} 张图片需要筛选")
            
            # 创建HelloKitty文件夹
            hellokitty_dir = self.download_dir.parent / "HelloKitty"
            hellokitty_dir.mkdir(exist_ok=True)
            
            # 初始化AI客户端
            ai_client = self._get_ai_client()
            if not ai_client:
                logger.warning("AI客户端初始化失败，跳过图片筛选")
                return
            
            # 筛选HelloKitty图片
            hellokitty_count = 0
            for image_file in image_files:
                try:
                    # 使用AI分析图片
                    is_hellokitty = await self._analyze_image_for_hellokitty(ai_client, str(image_file))
                    
                    if is_hellokitty:
                        # 复制到HelloKitty文件夹
                        dest_file = hellokitty_dir / image_file.name
                        import shutil
                        shutil.copy2(image_file, dest_file)
                        hellokitty_count += 1
                        logger.info(f"复制HelloKitty图片: {image_file.name}")
                    else:
                        logger.info(f"跳过非HelloKitty图片: {image_file.name}")
                        
                except Exception as e:
                    logger.warning(f"筛选图片失败 {image_file.name}: {e}")
                    # 筛选失败时保留图片
            
            logger.info(f"筛选完成，复制了 {hellokitty_count}/{len(image_files)} 张HelloKitty图片到 {hellokitty_dir}")
            
        except Exception as e:
            logger.error(f"图片筛选和复制失败: {e}")
    
    def _get_ai_client(self):
        """获取AI客户端"""
        try:
            from core.ai_client import AIClientManager, AIProvider
            from core.config import QQChannelConfig
            
            config = QQChannelConfig()
            
            # 使用配置中指定的AI提供商，如果没有配置则使用OpenRouter
            preferred_provider = getattr(config, 'ai_preferred_provider', 'openrouter')
            
            # 尝试使用配置的提供商
            try:
                if preferred_provider == 'gemini':
                    provider_enum = AIProvider.GEMINI
                elif preferred_provider == 'github_models':
                    provider_enum = AIProvider.GITHUB_MODELS
                elif preferred_provider == 'cherrystudio':
                    provider_enum = AIProvider.CHERRYSTUDIO
                elif preferred_provider == 'openrouter':
                    provider_enum = AIProvider.OPENROUTER
                else:
                    # 默认使用OpenRouter
                    provider_enum = AIProvider.OPENROUTER
                
                ai_manager = AIClientManager(config, provider_enum)
                logger.info(f"使用AI提供商: {preferred_provider}")
                return ai_manager
                
            except Exception as e:
                logger.warning(f"配置的AI提供商 {preferred_provider} 初始化失败: {e}")
                
                # 尝试备用提供商
                backup_providers = [
                    AIProvider.OPENROUTER,
                    AIProvider.GITHUB_MODELS,
                    AIProvider.CHERRYSTUDIO,
                    AIProvider.GEMINI
                ]
                
                for backup_provider in backup_providers:
                    if backup_provider != provider_enum:
                        try:
                            ai_manager = AIClientManager(config, backup_provider)
                            logger.info(f"使用备用AI提供商: {backup_provider.value}")
                            return ai_manager
                        except Exception as backup_e:
                            logger.warning(f"备用AI提供商 {backup_provider.value} 初始化失败: {backup_e}")
                            continue
                
                logger.error("所有AI提供商都初始化失败")
                return None
                
        except Exception as e:
            logger.error(f"AI客户端初始化失败: {e}")
            return None
    
    async def _analyze_image_for_hellokitty(self, ai_client, image_path: str) -> bool:
        """分析图片是否包含HelloKitty元素"""
        try:
            # 构建优化的HelloKitty识别提示词
            prompt = """
            请分析这张图片是否包含HelloKitty元素。
            
            HelloKitty特征：
            - 白色小猫形象，通常戴着蝴蝶结
            - 可爱的卡通风格，大眼睛，无嘴巴
            - HelloKitty品牌相关商品或图案
            - 粉色、红色、蓝色等HelloKitty常见颜色
            - 可能出现在服装、饰品、玩具、文具等物品上
            
            请只回答：是 或 否
            """
            
            # 获取可用的AI客户端
            if hasattr(ai_client, 'get_available_client'):
                client = await ai_client.get_available_client()
                logger.debug(f"使用AI客户端管理器，获取到客户端: {type(client).__name__}")
            else:
                client = ai_client
                logger.debug(f"直接使用AI客户端: {type(client).__name__}")
            
            # 检查图片文件是否存在
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return False
            
            # 检查图片文件大小
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                logger.error(f"图片文件为空: {image_path}")
                return False
            
            logger.info(f"开始分析图片: {image_path} (大小: {file_size} bytes)")
            
            # 调用AI分析
            result = await client.analyze_image(image_path, prompt)
            
            if result.success:
                # 解析AI响应
                content = result.content.strip().lower()
                is_hellokitty = "是" in content or "yes" in content or "true" in content
                
                # 记录分析结果
                logger.info(f"AI分析成功: {image_path}")
                logger.info(f"  AI响应: {result.content.strip()}")
                logger.info(f"  识别结果: {'HelloKitty' if is_hellokitty else '非HelloKitty'}")
                logger.info(f"  置信度: {result.confidence}")
                logger.info(f"  提供商: {result.metadata.get('provider', 'unknown')}")
                
                return is_hellokitty
            else:
                logger.warning(f"AI分析失败: {image_path}")
                logger.warning(f"  错误信息: {result.error}")
                logger.warning(f"  错误代码: {result.metadata.get('error_code', 'unknown')}")
                
                # 如果是配额限制错误，尝试使用备用策略
                if "quota" in result.error.lower() or "rate limit" in result.error.lower():
                    logger.info("检测到配额限制，尝试使用备用识别策略...")
                    return await self._fallback_recognition(image_path)
                
                return False
                
        except FileNotFoundError:
            logger.error(f"图片文件未找到: {image_path}")
            return False
        except PermissionError:
            logger.error(f"没有权限访问图片文件: {image_path}")
            return False
        except Exception as e:
            logger.error(f"图片分析过程中发生异常: {image_path}")
            logger.error(f"  异常类型: {type(e).__name__}")
            logger.error(f"  异常信息: {str(e)}")
            import traceback
            logger.debug(f"  异常堆栈: {traceback.format_exc()}")
            
            # 异常情况下也尝试备用策略
            logger.info("尝试使用备用识别策略...")
            return await self._fallback_recognition(image_path)
    
    async def _fallback_recognition(self, image_path: str) -> bool:
        """备用识别策略 - 基于文件名和路径的启发式判断"""
        try:
            # 检查文件名是否包含HelloKitty相关关键词
            filename = os.path.basename(image_path).lower()
            path_parts = image_path.lower().split('/')
            
            # HelloKitty相关关键词
            hellokitty_keywords = [
                'hellokitty', 'hello_kitty', 'hello-kitty', 'kitty', 'hello',
                'sanrio', 'kawaii', 'cute', 'cat', 'pink', 'bow'
            ]
            
            # 检查文件名
            for keyword in hellokitty_keywords:
                if keyword in filename:
                    logger.info(f"基于文件名关键词识别为HelloKitty: {filename} (关键词: {keyword})")
                    return True
            
            # 检查路径
            for part in path_parts:
                for keyword in hellokitty_keywords:
                    if keyword in part:
                        logger.info(f"基于路径关键词识别为HelloKitty: {part} (关键词: {keyword})")
                        return True
            
            # 如果没有明确的关键词，使用保守策略
            # 对于HelloKitty频道，假设大部分图片都是HelloKitty相关的
            logger.info(f"使用保守策略，假设图片为HelloKitty: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"备用识别策略失败: {e}")
            # 备用策略失败时，使用保守策略
            return True

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