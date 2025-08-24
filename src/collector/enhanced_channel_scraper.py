#!/usr/bin/env python3
"""
增强版QQ频道抓取器，集成JSON-LD数据提取
"""

import sys
import json
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from core.browser import BrowserManager
from core.config import QQChannelConfig
from models.post import QQChannelPost
from models.channel import QQChannel
# JSON提取功能已整合到本类中

logger = logging.getLogger(__name__)

class EnhancedQQChannelScraper:
    """增强版QQ频道抓取器，优先使用JSON数据"""
    
    def __init__(self, config: QQChannelConfig):
        self.config = config
        self.browser_manager = BrowserManager(config)
        
        # 传统CSS选择器作为备用
        self.fallback_selectors = {
            'post_container': [
                'div[class*="post"]',
                'div[class*="item"]',
                'div[class*="feed"]',
                'div[class*="message"]',
                'article',
                'div[class*="content"]'
            ]
        }
    
    async def scrape_channel_posts(self, channel_url: str, max_posts: int = 100) -> List[QQChannelPost]:
        """抓取频道帖子，优先使用JSON数据"""
        logger.info(f"开始抓取频道帖子: {channel_url}")
        
        try:
            # 方法1: 尝试JSON-LD数据提取（推荐）
            logger.info("🔍 尝试JSON-LD数据提取...")
            posts = await self._extract_posts_from_json(channel_url)
            
            if posts:
                logger.info(f"✅ JSON数据提取成功: {len(posts)} 个帖子")
                return posts[:max_posts]
            
            # 方法2: 回退到传统CSS选择器方法
            logger.info("⚠️  JSON提取失败，使用传统CSS方法...")
            posts = await self._scrape_with_css_selectors(channel_url, max_posts)
            
            if posts:
                logger.info(f"✅ CSS选择器提取成功: {len(posts)} 个帖子")
                return posts
            
            # 方法3: 混合方法 - 页面源码分析
            logger.info("🔧 使用页面源码分析方法...")
            posts = await self._scrape_with_source_analysis(channel_url, max_posts)
            
            logger.info(f"📊 最终提取结果: {len(posts)} 个帖子")
            return posts
            
        except Exception as e:
            logger.error(f"帖子抓取失败: {e}")
            return []
    
    async def _scrape_with_css_selectors(self, url: str, max_posts: int) -> List[QQChannelPost]:
        """使用传统CSS选择器方法"""
        posts = []
        
        try:
            self.browser_manager.create_driver()
            self.browser_manager.driver.get(url)
            
            # 等待页面加载
            import time
            time.sleep(3)
            
            # 尝试不同的选择器
            for selector in self.fallback_selectors['post_container']:
                try:
                    elements = self.browser_manager.driver.find_elements(
                        "css selector", selector
                    )
                    if elements:
                        logger.info(f"找到 {len(elements)} 个元素使用选择器: {selector}")
                        break
                except:
                    continue
            
            # TODO: 解析CSS选择器找到的元素
            logger.info("CSS选择器方法需要进一步开发")
            
        except Exception as e:
            logger.error(f"CSS选择器方法失败: {e}")
        finally:
            try:
                self.browser_manager.close_driver()
            except:
                pass
        
        return posts
    
    async def _scrape_with_source_analysis(self, url: str, max_posts: int) -> List[QQChannelPost]:
        """使用页面源码分析方法"""
        posts = []
        
        try:
            self.browser_manager.create_driver()
            self.browser_manager.driver.get(url)
            
            # 等待页面加载
            import time
            time.sleep(5)
            
            # 获取页面源码
            page_source = self.browser_manager.driver.page_source
            
            # 方法1: 从script标签提取
            posts.extend(self._extract_from_script_tags(page_source))
            
            # 方法2: 从HTML元素提取视频
            posts.extend(await self._extract_videos_from_html())
            
            # 方法3: 从CSS选择器提取
            posts.extend(await self._extract_posts_from_css())
            
            # 去重
            unique_posts = self._deduplicate_posts(posts)
            
            return unique_posts[:max_posts]
            
        except Exception as e:
            logger.error(f"页面源码分析失败: {e}")
            return []
        finally:
            self.browser_manager.close_driver()
    
    async def _extract_videos_from_html(self) -> List[QQChannelPost]:
        """从HTML中提取视频内容"""
        posts = []
        
        try:
            # 查找视频元素
            video_elements = self.browser_manager.driver.find_elements("css selector", "video")
            logger.info(f"找到 {len(video_elements)} 个视频元素")
            
            for video_elem in video_elements:
                try:
                    # 获取视频信息
                    video_src = video_elem.get_attribute("src")
                    video_poster = video_elem.get_attribute("poster")
                    
                    if video_src:
                        # 查找父级容器，获取帖子信息
                        post_container = self._find_post_container(video_elem)
                        if post_container:
                            post = self._create_post_from_video_element(post_container, video_src, video_poster)
                            if post:
                                posts.append(post)
                
                except Exception as e:
                    logger.warning(f"提取视频元素失败: {e}")
                    continue
            
            # 查找包含视频的帖子容器
            video_containers = self.browser_manager.driver.find_elements(
                "css selector", 
                "div[class*='post'], div[class*='item'], div[class*='feed']"
            )
            
            for container in video_containers:
                try:
                    # 检查是否包含视频
                    videos_in_container = container.find_elements("css selector", "video")
                    if videos_in_container:
                        post = self._create_post_from_container(container)
                        if post:
                            posts.append(post)
                
                except Exception as e:
                    logger.warning(f"提取视频容器失败: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"HTML视频提取失败: {e}")
            return []
    
    def _find_post_container(self, element):
        """查找帖子的父级容器"""
        try:
            # 向上查找包含帖子信息的容器
            current = element
            for _ in range(10):  # 最多向上查找10层
                if current is None:
                    break
                
                # 检查是否包含帖子信息
                if self._is_post_container(current):
                    return current
                
                current = current.find_element("xpath", "..")
            
            return None
            
        except Exception:
            return None
    
    def _is_post_container(self, element):
        """判断元素是否为帖子容器"""
        try:
            # 检查是否包含帖子特征
            text = element.text.lower()
            if any(keyword in text for keyword in ['小时前', '分钟前', '点赞', '评论', '分享']):
                return True
            
            # 检查类名
            class_name = element.get_attribute("class") or ""
            if any(keyword in class_name.lower() for keyword in ['post', 'item', 'feed', 'message']):
                return True
            
            return False
            
        except Exception:
            return False
    
    def _create_post_from_video_element(self, container, video_src, video_poster):
        """从视频元素创建帖子对象"""
        try:
            # 提取帖子信息
            text_content = container.text
            lines = text_content.split('\n')
            
            # 提取作者和时间
            author_name = "未知"
            post_time_str = "未知"
            
            for line in lines:
                if '小时前' in line or '分钟前' in line:
                    post_time_str = line.strip()
                elif not any(keyword in line for keyword in ['小时前', '分钟前', '点赞', '评论', '分享']):
                    if len(line.strip()) > 2:
                        author_name = line.strip()
                        break
            
            # 创建帖子对象
            post = QQChannelPost(
                post_id=f"video_{hash(video_src) % 100000}",
                channel_id="5yy11f95s1",
                channel_name="HelloKitty",
                author_name=author_name,
                title="视频帖子",
                content=text_content[:200] + "..." if len(text_content) > 200 else text_content,
                images=[video_poster] if video_poster else [],
                videos=[video_src],
                post_time=self._parse_natural_time_to_datetime(post_time_str),  # 真实时间用于逻辑
                post_time_str=post_time_str,  # 相对时间字符串用于展示
                like_count=0,
                comment_count=0
            )
            
            return post
            
        except Exception as e:
            logger.warning(f"从视频元素创建帖子失败: {e}")
            return None
    
    def _create_post_from_container(self, container):
        """从容器创建帖子对象"""
        try:
            # 提取文本内容
            text_content = container.text
            lines = text_content.split('\n')
            
            # 提取视频URL
            videos = []
            try:
                video_elements = container.find_elements("css selector", "video")
                for video_elem in video_elements:
                    video_src = video_elem.get_attribute("src")
                    if video_src:
                        videos.append(video_src)
            except:
                pass
            
            # 提取图片和动图URL
            images = []
            gifs = []
            try:
                img_elements = container.find_elements("css selector", "img")
                for img_elem in img_elements:
                    img_src = img_elem.get_attribute("src")
                    if img_src and not img_src.endswith('.svg'):
                        # 检测是否为GIF
                        if img_src.lower().endswith('.gif') or 'gif' in img_src.lower():
                            gifs.append(img_src)
                        else:
                            images.append(img_src)
            except:
                pass
            
            # 提取基本信息
            author_name = "未知"
            post_time_str = "未知"
            content = ""
            
            for line in lines:
                if '小时前' in line or '分钟前' in line:
                    post_time_str = line.strip()
                elif not any(keyword in line for keyword in ['小时前', '分钟前', '点赞', '评论', '分享']):
                    if len(line.strip()) > 2:
                        if not author_name or author_name == "未知":
                            author_name = line.strip()
                        else:
                            content += line.strip() + " "
            
            # 创建帖子对象
            post = QQChannelPost(
                post_id=f"container_{hash(text_content) % 100000}",
                channel_id="5yy11f95s1",
                channel_name="HelloKitty",
                author_name=author_name,
                title="帖子内容",
                content=content.strip() or "包含媒体内容的帖子",
                images=images,
                gifs=gifs,
                videos=videos,
                post_time=self._parse_natural_time_to_datetime(post_time_str),  # 真实时间用于逻辑
                post_time_str=post_time_str,  # 相对时间字符串用于展示
                like_count=0,
                comment_count=0
            )
            
            return post
            
        except Exception as e:
            logger.warning(f"从容器创建帖子失败: {e}")
            return None
    
    def _deduplicate_posts(self, posts):
        """去重帖子"""
        seen_ids = set()
        unique_posts = []
        
        for post in posts:
            if post.post_id not in seen_ids:
                seen_ids.add(post.post_id)
                unique_posts.append(post)
        
        return unique_posts
    
    async def _extract_posts_from_json(self, url: str):
        """从页面JSON数据中提取帖子"""
        logger.info(f"🔍 从JSON数据提取帖子: {url}")
        
        try:
            self.browser_manager.create_driver()
            self.browser_manager.driver.get(url)
            
            # 等待页面加载
            import time
            time.sleep(3)
            
            # 获取页面HTML
            html = self.browser_manager.driver.page_source
            
            # 查找JSON-LD数据
            json_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            json_matches = re.findall(json_pattern, html, re.DOTALL)
            
            posts = []
            
            for json_str in json_matches:
                try:
                    data = json.loads(json_str.strip())
                    posts.extend(self._parse_json_data(data))
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️  JSON解析失败: {e}")
                    continue
            
            # 如果没有找到JSON-LD，尝试查找其他JSON数据
            if not posts:
                posts = self._extract_from_script_tags(html)
            
            logger.info(f"✅ 成功提取 {len(posts)} 个帖子")
            
            return posts
            
        except Exception as e:
            logger.error(f"❌ 提取失败: {e}")
            return []
        finally:
            try:
                self.browser_manager.close_driver()
            except:
                pass
    
    def _parse_json_data(self, data):
        """解析JSON-LD数据"""
        posts = []
        
        if isinstance(data, dict):
            # 查找@graph或itemListElement
            if '@graph' in data:
                for graph_item in data['@graph']:
                    if graph_item.get('@type') == 'ItemList':
                        posts.extend(self._parse_item_list(graph_item))
        
        return posts
    
    def _parse_item_list(self, item_list):
        """解析ItemList中的帖子"""
        posts = []
        
        if 'itemListElement' in item_list:
            for item in item_list['itemListElement']:
                if 'item' in item:
                    post_data = item['item']
                    if post_data.get('@type') == 'SocialMediaPosting':
                        post = self._create_post_from_json(post_data)
                        if post:
                            posts.append(post)
        
        return posts
    
    def _create_post_from_json(self, post_data):
        """从JSON数据创建Post对象"""
        try:
            # 提取基本信息
            title = post_data.get('headline', '').strip()
            content = post_data.get('description', '').strip()
            url = post_data.get('url', '')
            
            # 提取时间
            date_published = post_data.get('datePublished', '')
            
            # 提取作者
            author_info = post_data.get('author', {})
            author_name = author_info.get('name', '未知') if isinstance(author_info, dict) else '未知'
            
            # 提取互动数据
            interaction = post_data.get('interactionStatistic', {})
            like_count = interaction.get('userInteractionCount', 0) if isinstance(interaction, dict) else 0
            
            # 提取图片
            images = post_data.get('image', [])
            if isinstance(images, str):
                images = [images]
            elif not isinstance(images, list):
                images = []
            
            # 提取动图（GIF）
            gifs = post_data.get('gif', [])
            if isinstance(gifs, str):
                gifs = [gifs]
            elif not isinstance(gifs, list):
                gifs = []
            
            # 提取视频 - 支持VideoObject格式
            videos = []
            video_data = post_data.get('video', {})
            
            if isinstance(video_data, dict) and video_data.get('@type') == 'VideoObject':
                # 从VideoObject中提取视频URL
                video_url = video_data.get('contentUrl')
                if video_url:
                    videos.append(video_url)
            elif isinstance(video_data, str):
                videos = [video_data]
            elif isinstance(video_data, list):
                for video_item in video_data:
                    if isinstance(video_item, dict) and video_item.get('@type') == 'VideoObject':
                        video_url = video_item.get('contentUrl')
                        if video_url:
                            videos.append(video_url)
                    elif isinstance(video_item, str):
                        videos.append(video_item)
            
            # 从URL提取帖子ID
            post_id = self._extract_post_id(url)
            
            # 创建Post对象
            post = QQChannelPost(
                post_id=post_id,
                channel_id="5yy11f95s1",  # HelloKitty频道ID
                channel_name="HelloKitty",
                author_name=author_name,
                title=title,
                content=content,
                images=images,
                gifs=gifs,
                videos=videos,
                like_count=like_count,
                comment_count=0,  # JSON中没有评论数
                post_url=url,
                post_time=self._parse_datetime_obj(date_published)
            )
            
            return post
            
        except Exception as e:
            logger.warning(f"⚠️  创建帖子对象失败: {e}")
            return None
    
    def _extract_from_script_tags(self, html):
        """从script标签中查找帖子数据"""
        posts = []
        
        # 查找包含帖子信息的script标签
        script_pattern = r'<script[^>]*>(.*?)</script>'
        script_matches = re.findall(script_pattern, html, re.DOTALL)
        
        for script_content in script_matches:
            if 'SocialMediaPosting' in script_content or 'hellokitty' in script_content.lower():
                # 尝试从script中提取JSON数据
                try:
                    # 查找JSON对象
                    json_pattern = r'\{[^{}]*"@type"[^{}]*"SocialMediaPosting"[^{}]*\}'
                    json_objects = re.findall(json_pattern, script_content, re.DOTALL)
                    
                    for json_str in json_objects:
                        try:
                            data = json.loads(json_str)
                            post = self._create_post_from_json(data)
                            if post:
                                posts.append(post)
                        except:
                            continue
                except:
                    continue
        
        return posts
    
    async def _extract_posts_from_css(self) -> List[QQChannelPost]:
        """使用CSS选择器提取帖子"""
        posts = []
        
        try:
            # 尝试不同的CSS选择器
            selectors = [
                'div[class*="post"]',
                'div[class*="item"]', 
                'div[class*="feed"]',
                'div[class*="message"]',
                'article',
                'div[class*="content"]'
            ]
            
            for selector in selectors:
                try:
                    elements = self.browser_manager.driver.find_elements("css selector", selector)
                    if elements:
                        logger.info(f"使用选择器 {selector} 找到 {len(elements)} 个元素")
                        
                        for element in elements[:10]:  # 限制数量
                            try:
                                post = self._create_post_from_css_element(element)
                                if post:
                                    posts.append(post)
                            except Exception as e:
                                logger.warning(f"从CSS元素创建帖子失败: {e}")
                                continue
                        
                        if posts:
                            break
                            
                except Exception as e:
                    logger.warning(f"CSS选择器 {selector} 失败: {e}")
                    continue
            
            return posts
            
        except Exception as e:
            logger.error(f"CSS选择器提取失败: {e}")
            return []
    
    def _create_post_from_css_element(self, element):
        """从CSS元素创建帖子对象"""
        try:
            # 提取文本内容
            text_content = element.text
            if not text_content or len(text_content.strip()) < 10:
                return None
            
            lines = text_content.split('\n')
            
            # 提取视频URL
            videos = []
            try:
                video_elements = element.find_elements("css selector", "video")
                for video_elem in video_elements:
                    video_src = video_elem.get_attribute("src")
                    if video_src:
                        videos.append(video_src)
            except:
                pass
            
            # 提取图片URL
            images = []
            try:
                img_elements = element.find_elements("css selector", "img")
                for img_elem in img_elements:
                    img_src = img_elem.get_attribute("src")
                    if img_src and not img_src.endswith('.svg'):
                        images.append(img_src)
            except:
                pass
            
            # 提取基本信息
            author_name = "未知"
            post_time_str = "未知"
            content = ""
            
            for line in lines:
                if '小时前' in line or '分钟前' in line:
                    post_time_str = line.strip()
                elif not any(keyword in line for keyword in ['小时前', '分钟前', '点赞', '评论', '分享']):
                    if len(line.strip()) > 2:
                        if not author_name or author_name == "未知":
                            author_name = line.strip()
                        else:
                            content += line.strip() + " "
            
            # 创建帖子对象
            post = QQChannelPost(
                post_id=f"css_{hash(text_content) % 100000}",
                channel_id="5yy11f95s1",
                channel_name="HelloKitty",
                title="CSS提取的帖子",
                content=content.strip() or "包含媒体内容的帖子",
                images=images,
                videos=videos,
                post_time=self._parse_natural_time_to_datetime(post_time_str),  # 真实时间用于逻辑
                post_time_str=post_time_str,  # 相对时间字符串用于展示
                like_count=0,
                comment_count=0
            )
            
            return post
            
        except Exception as e:
            logger.warning(f"从CSS元素创建帖子失败: {e}")
            return None
    
    def _parse_datetime_obj(self, date_str):
        """解析日期时间为datetime对象"""
        if not date_str:
            return None
        
        try:
            # 解析ISO格式日期
            from datetime import datetime
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt
        except:
            return None
    
    def _parse_natural_time_to_datetime(self, time_str):
        """将自然语言时间转换为datetime对象"""
        if not time_str:
            return None
        
        try:
            from datetime import datetime, timedelta
            import re
            
            now = datetime.now()
            time_str = time_str.strip()
            
            # 处理"X秒前"
            seconds_match = re.search(r'(\d+)秒前', time_str)
            if seconds_match:
                seconds = int(seconds_match.group(1))
                return now - timedelta(seconds=seconds)
            
            # 处理"X分钟前"
            minutes_match = re.search(r'(\d+)分钟前', time_str)
            if minutes_match:
                minutes = int(minutes_match.group(1))
                return now - timedelta(minutes=minutes)
            
            # 处理"X小时前"
            hours_match = re.search(r'(\d+)小时前', time_str)
            if hours_match:
                hours = int(hours_match.group(1))
                return now - timedelta(hours=hours)
            
            # 处理"X天前"
            days_match = re.search(r'(\d+)天前', time_str)
            if days_match:
                days = int(days_match.group(1))
                return now - timedelta(days=days)
            
            # 处理"昨天"
            if '昨天' in time_str:
                return now - timedelta(days=1)
            
            # 处理"前天"
            if '前天' in time_str:
                return now - timedelta(days=2)
            
            # 处理MM-DD格式
            date_match = re.search(r'(\d{1,2})-(\d{1,2})', time_str)
            if date_match:
                month = int(date_match.group(1))
                day = int(date_match.group(2))
                # 假设是今年的日期
                try:
                    return datetime(now.year, month, day)
                except ValueError:
                    # 如果日期无效，返回None
                    return None
            
            # 如果无法解析，返回None
            return None
            
        except Exception as e:
            logger.warning(f"自然语言时间解析失败: {time_str}, {e}")
            return None
    
    def _extract_post_id(self, url):
        """从URL中提取帖子ID"""
        if not url:
            return "unknown"
        
        # 从URL中提取ID部分
        try:
            parts = url.split('/')
            for part in reversed(parts):
                if part and 'B_' in part:
                    return part
        except:
            pass
        
        return f"post_{hash(url) % 100000}"

async def test_enhanced_scraper():
    """测试增强版抓取器"""
    print("🔧 测试增强版QQ频道抓取器")
    print("="*40)
    
    config = QQChannelConfig()
    scraper = EnhancedQQChannelScraper(config)
    
    # 测试HelloKitty频道
    url = "https://pd.qq.com/g/5yy11f95s1"
    posts = await scraper.scrape_channel_posts(url, max_posts=10)
    
    print(f"📊 测试结果: {len(posts)} 个帖子")
    
    for i, post in enumerate(posts[:3], 1):
        print(f"   {i}. {post.title}")
        print(f"      作者: {post.author_name}")
        print(f"      图片: {len(post.images)} 张")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_enhanced_scraper())
