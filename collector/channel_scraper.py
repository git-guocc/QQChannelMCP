"""
QQ频道爬虫模块
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ..core.browser import BrowserManager
from ..core.config import QQChannelConfig
from ..core.exceptions import ScrapingError, handle_exception
from ..models.post import QQChannelPost
from ..models.channel import QQChannel
from .content_parser import ContentParser

logger = logging.getLogger(__name__)


class QQChannelScraper:
    """QQ频道爬虫"""
    
    def __init__(self, config: Optional[QQChannelConfig] = None):
        self.config = config or QQChannelConfig()
        self.browser_manager = BrowserManager(self.config)
        self.content_parser = ContentParser()
        
        # QQ频道常用选择器
        self.selectors = {
            'post_container': [
                '.message-item',
                '[data-v-message]',
                '.chat-message',
                '.post-item',
                '.content-item'
            ],
            'author_name': [
                '.nickname',
                '.username',
                '.author-name',
                '.sender-name',
                '[class*="nick"]'
            ],
            'post_content': [
                '.message-content',
                '.post-content',
                '.text-content',
                '.content-text',
                '[class*="content"]'
            ],
            'post_time': [
                '.time',
                '.timestamp',
                '.post-time',
                '[class*="time"]'
            ],
            'images': [
                '.image-content img',
                '.msg-image img',
                '.photo img',
                'img[src*="image"]'
            ],
            'like_count': [
                '.like-count',
                '[class*="like"] .count',
                '.reaction-count'
            ],
            'comment_count': [
                '.comment-count',
                '[class*="comment"] .count',
                '.reply-count'
            ]
        }
    
    @handle_exception
    async def scrape_channel_posts(self, channel_url: str, max_posts: int = 100) -> List[QQChannelPost]:
        """
        采集频道帖子
        
        Args:
            channel_url: 频道URL
            max_posts: 最大采集数量
            
        Returns:
            帖子列表
        """
        logger.info(f"开始采集QQ频道: {channel_url}, 最大数量: {max_posts}")
        
        posts = []
        
        try:
            # 创建浏览器实例
            with self.browser_manager as browser:
                # 访问频道页面
                await browser.navigate_to(channel_url)
                
                # 解析频道信息
                channel_info = await self._parse_channel_info(browser, channel_url)
                
                # 滚动并收集帖子元素
                post_elements = await browser.scroll_and_collect(
                    max_items=max_posts,
                    item_selector=self._get_primary_selector('post_container')
                )
                
                logger.info(f"找到 {len(post_elements)} 个帖子元素")
                
                # 解析每个帖子
                for i, element in enumerate(post_elements):
                    try:
                        post = await self._parse_post_element(element, channel_info, i)
                        if post and post.has_content():
                            posts.append(post)
                            
                        # 添加延迟避免过快操作
                        await asyncio.sleep(self.config.request_delay)
                        
                    except Exception as e:
                        logger.warning(f"解析第 {i+1} 个帖子失败: {e}")
                        continue
                
        except Exception as e:
            raise ScrapingError(f"采集频道失败: {str(e)}")
        
        logger.info(f"成功采集 {len(posts)} 个帖子")
        return posts
    
    async def _parse_channel_info(self, browser: BrowserManager, channel_url: str) -> Dict[str, Any]:
        """解析频道基础信息"""
        try:
            channel_info = {
                'channel_url': channel_url,
                'channel_id': self._extract_channel_id(channel_url),
                'channel_name': self._safe_get_text(browser, ['.channel-name', '.group-name', 'title']),
                'description': self._safe_get_text(browser, ['.channel-desc', '.group-desc']),
                'member_count': self._parse_number(self._safe_get_text(browser, ['.member-count', '.members'])),
            }
            
            # 尝试获取频道名称
            if not channel_info['channel_name']:
                title = browser.driver.title
                channel_info['channel_name'] = title.split('-')[0].strip() if '-' in title else title
            
            logger.info(f"频道信息: {channel_info['channel_name']}")
            return channel_info
            
        except Exception as e:
            logger.warning(f"解析频道信息失败: {e}")
            return {
                'channel_url': channel_url,
                'channel_id': self._extract_channel_id(channel_url),
                'channel_name': 'Unknown Channel',
                'description': '',
                'member_count': 0
            }
    
    async def _parse_post_element(self, element, channel_info: Dict, index: int) -> Optional[QQChannelPost]:
        """解析单个帖子元素"""
        try:
            # 生成帖子ID
            post_id = f"{channel_info['channel_id']}_{index}_{int(datetime.now().timestamp())}"
            
            # 提取基础信息
            author_name = self._safe_get_element_text(element, self.selectors['author_name'])
            content = self._safe_get_element_text(element, self.selectors['post_content'])
            time_text = self._safe_get_element_text(element, self.selectors['post_time'])
            
            # 解析时间
            post_time = self.content_parser.parse_time(time_text)
            
            # 提取图片
            images = self._extract_images_from_element(element)
            
            # 提取互动数据
            like_count = self._parse_number(self._safe_get_element_text(element, self.selectors['like_count']))
            comment_count = self._parse_number(self._safe_get_element_text(element, self.selectors['comment_count']))
            
            # 判断帖子类型
            post_type = "image" if images else "text"
            
            # 创建帖子对象
            post = QQChannelPost(
                post_id=post_id,
                channel_id=channel_info['channel_id'],
                channel_name=channel_info['channel_name'],
                author_name=author_name or "Anonymous",
                content=content,
                images=images,
                post_time=post_time,
                like_count=like_count,
                comment_count=comment_count,
                post_type=post_type,
                post_url=f"{channel_info['channel_url']}#{post_id}",
                collected_time=datetime.now()
            )
            
            return post
            
        except Exception as e:
            logger.error(f"解析帖子元素失败: {e}")
            return None
    
    def _safe_get_text(self, browser: BrowserManager, selectors: List[str]) -> str:
        """安全获取文本"""
        for selector in selectors:
            element = browser.find_element_safe(By.CSS_SELECTOR, selector)
            if element:
                text = browser.get_element_text_safe(element)
                if text:
                    return text
        return ""
    
    def _safe_get_element_text(self, parent_element, selectors: List[str]) -> str:
        """从父元素中安全获取文本"""
        for selector in selectors:
            try:
                element = parent_element.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text:
                    return text
            except (NoSuchElementException, Exception):
                continue
        return ""
    
    def _extract_images_from_element(self, element) -> List[str]:
        """从元素中提取图片URLs"""
        images = []
        
        for selector in self.selectors['images']:
            try:
                img_elements = element.find_elements(By.CSS_SELECTOR, selector)
                for img in img_elements:
                    src = img.get_attribute('src') or img.get_attribute('data-src')
                    if src and self._is_valid_image_url(src):
                        # 转换为完整URL
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = 'https://qpic.cn' + src  # QQ图片域名
                        
                        if src not in images:
                            images.append(src)
                        
            except Exception as e:
                logger.debug(f"提取图片失败: {e}")
                continue
        
        return images
    
    def _is_valid_image_url(self, url: str) -> bool:
        """检查是否为有效的图片URL"""
        if not url:
            return False
        
        # 检查是否为图片扩展名
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        parsed_url = urlparse(url.lower())
        
        # 检查扩展名
        path = parsed_url.path
        if any(path.endswith(ext) for ext in image_extensions):
            return True
        
        # QQ图片URL特征
        if 'qpic.cn' in url or 'gtimg.cn' in url or 'qq.com' in url:
            return True
        
        # 包含图片关键词
        if any(keyword in url.lower() for keyword in ['image', 'img', 'photo', 'pic']):
            return True
        
        return False
    
    def _extract_channel_id(self, channel_url: str) -> str:
        """从URL中提取频道ID"""
        try:
            # QQ频道URL格式：https://pd.qq.com/s/channel_id
            parsed = urlparse(channel_url)
            path_parts = parsed.path.strip('/').split('/')
            
            if 's' in path_parts and len(path_parts) > path_parts.index('s'):
                return path_parts[path_parts.index('s') + 1]
            
            # 如果无法提取，使用URL哈希作为ID
            return str(abs(hash(channel_url)))[:10]
            
        except Exception:
            return str(abs(hash(channel_url)))[:10]
    
    def _parse_number(self, text: str) -> int:
        """解析数字文本"""
        if not text:
            return 0
        
        try:
            # 移除所有非数字字符
            numbers = re.findall(r'\d+', text)
            if numbers:
                return int(numbers[0])
        except Exception:
            pass
        
        return 0
    
    def _get_primary_selector(self, selector_key: str) -> str:
        """获取主要选择器"""
        selectors = self.selectors.get(selector_key, [])
        return selectors[0] if selectors else ""
    
    @handle_exception
    async def get_channel_info(self, channel_url: str) -> QQChannel:
        """获取频道详细信息"""
        logger.info(f"获取频道信息: {channel_url}")
        
        try:
            with self.browser_manager as browser:
                await browser.navigate_to(channel_url)
                
                # 解析频道信息
                channel_info = await self._parse_channel_info(browser, channel_url)
                
                # 创建频道对象
                channel = QQChannel(
                    channel_id=channel_info['channel_id'],
                    channel_name=channel_info['channel_name'],
                    channel_url=channel_url,
                    description=channel_info['description'],
                    member_count=channel_info['member_count'],
                    discovered_time=datetime.now()
                )
                
                return channel
                
        except Exception as e:
            raise ScrapingError(f"获取频道信息失败: {str(e)}")
    
    async def test_connection(self, channel_url: str) -> Dict[str, Any]:
        """测试频道连接"""
        try:
            with self.browser_manager as browser:
                await browser.navigate_to(channel_url)
                
                # 检查页面是否正常加载
                title = browser.driver.title
                current_url = browser.driver.current_url
                
                # 尝试找到一些关键元素
                post_elements = browser.find_elements_safe(
                    By.CSS_SELECTOR, 
                    self._get_primary_selector('post_container')
                )
                
                return {
                    'success': True,
                    'title': title,
                    'url': current_url,
                    'post_elements_found': len(post_elements),
                    'message': '连接成功'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '连接失败'
            }
