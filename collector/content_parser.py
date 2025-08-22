"""
内容解析模块
"""

import re
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class ContentParser:
    """内容解析器"""
    
    def __init__(self):
        # 时间解析正则表达式
        self.time_patterns = [
            (r'(\d+)分钟前', lambda m: datetime.now() - timedelta(minutes=int(m.group(1)))),
            (r'(\d+)小时前', lambda m: datetime.now() - timedelta(hours=int(m.group(1)))),
            (r'(\d+)天前', lambda m: datetime.now() - timedelta(days=int(m.group(1)))),
            (r'(\d+)周前', lambda m: datetime.now() - timedelta(weeks=int(m.group(1)))),
            (r'(\d+)个月前', lambda m: datetime.now() - timedelta(days=int(m.group(1)) * 30)),
            (r'昨天', lambda m: datetime.now() - timedelta(days=1)),
            (r'前天', lambda m: datetime.now() - timedelta(days=2)),
            (r'刚刚', lambda m: datetime.now()),
        ]
        
        # 数字解析映射
        self.number_units = {
            'k': 1000,
            'K': 1000,
            'w': 10000,
            'W': 10000,
            '万': 10000,
            '千': 1000,
            '百': 100,
        }
    
    def parse_time(self, time_text: str) -> Optional[datetime]:
        """
        解析时间文本
        
        Args:
            time_text: 时间文本
            
        Returns:
            解析后的时间对象
        """
        if not time_text:
            return None
        
        time_text = time_text.strip()
        
        try:
            # 尝试相对时间模式
            for pattern, converter in self.time_patterns:
                match = re.search(pattern, time_text)
                if match:
                    return converter(match)
            
            # 尝试解析具体时间格式
            # 例如：2024-01-15 14:30、01-15 14:30、14:30
            time_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%m-%d %H:%M',
                '%H:%M:%S',
                '%H:%M',
                '%Y年%m月%d日 %H:%M',
                '%m月%d日 %H:%M',
                '%Y年%m月%d日',
                '%m月%d日',
            ]
            
            for fmt in time_formats:
                try:
                    return datetime.strptime(time_text, fmt)
                except ValueError:
                    continue
            
            # 尝试使用dateutil解析
            return date_parser.parse(time_text, fuzzy=True)
            
        except Exception as e:
            logger.debug(f"时间解析失败: {time_text}, 错误: {e}")
            return None
    
    def parse_number(self, number_text: str) -> int:
        """
        解析数字文本（支持k、w等单位）
        
        Args:
            number_text: 数字文本
            
        Returns:
            解析后的数字
        """
        if not number_text:
            return 0
        
        try:
            # 清理文本
            text = number_text.strip().replace(',', '').replace(' ', '')
            
            # 提取数字和单位
            match = re.search(r'([\d.]+)([kwKW万千百]?)', text)
            if not match:
                return 0
            
            number_str, unit = match.groups()
            number = float(number_str)
            
            # 应用单位
            if unit in self.number_units:
                number *= self.number_units[unit]
            
            return int(number)
            
        except Exception as e:
            logger.debug(f"数字解析失败: {number_text}, 错误: {e}")
            return 0
    
    def extract_mentions(self, text: str) -> List[str]:
        """
        提取@提及
        
        Args:
            text: 文本内容
            
        Returns:
            提及的用户名列表
        """
        if not text:
            return []
        
        # 匹配@用户名模式
        pattern = r'@([a-zA-Z0-9_\u4e00-\u9fa5]+)'
        mentions = re.findall(pattern, text)
        
        return list(set(mentions))  # 去重
    
    def extract_hashtags(self, text: str) -> List[str]:
        """
        提取话题标签
        
        Args:
            text: 文本内容
            
        Returns:
            话题标签列表
        """
        if not text:
            return []
        
        # 匹配#话题#模式
        pattern = r'#([^#\s]+)#?'
        hashtags = re.findall(pattern, text)
        
        return list(set(hashtags))  # 去重
    
    def extract_urls(self, text: str) -> List[str]:
        """
        提取URL链接
        
        Args:
            text: 文本内容
            
        Returns:
            URL列表
        """
        if not text:
            return []
        
        # URL正则表达式
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        return list(set(urls))  # 去重
    
    def clean_text(self, text: str) -> str:
        """
        清理文本内容
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 移除特殊字符（保留中文、英文、数字、基本标点）
        text = re.sub(r'[^\w\s\u4e00-\u9fa5.,!?;:()[\]{}"""''""…—-]', '', text)
        
        return text.strip()
    
    def extract_keywords(self, text: str, min_length: int = 2) -> List[str]:
        """
        提取关键词
        
        Args:
            text: 文本内容
            min_length: 最小词长度
            
        Returns:
            关键词列表
        """
        if not text:
            return []
        
        # 简单的关键词提取（基于分词）
        # 这里使用简单的方法，实际项目中可以使用jieba等分词工具
        
        # 移除标点符号
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fa5]', ' ', text)
        
        # 分割单词
        words = clean_text.split()
        
        # 过滤长度和常见停用词
        stop_words = {'的', '了', '是', '在', '我', '你', '他', '她', '它', '和', '与', '或', '但', '而', '也', '都', '很', '更', '最'}
        
        keywords = []
        for word in words:
            word = word.strip()
            if len(word) >= min_length and word not in stop_words:
                keywords.append(word)
        
        return list(set(keywords))  # 去重
    
    def detect_post_type(self, content: str, images: List[str]) -> str:
        """
        检测帖子类型
        
        Args:
            content: 文本内容
            images: 图片列表
            
        Returns:
            帖子类型 (text/image/video)
        """
        # 检查是否有图片
        if images:
            return "image"
        
        # 检查是否有视频相关关键词
        video_keywords = ['视频', '播放', 'mp4', 'avi', '录像', '影片']
        if any(keyword in content.lower() for keyword in video_keywords):
            return "video"
        
        return "text"
    
    def extract_emotions(self, text: str) -> List[str]:
        """
        提取表情符号
        
        Args:
            text: 文本内容
            
        Returns:
            表情符号列表
        """
        if not text:
            return []
        
        # 匹配emoji和表情符号
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001f900-\U0001f9ff\U0001f600-\U0001f64f]+'
        
        emojis = re.findall(emoji_pattern, text)
        
        # 匹配文字表情
        text_emotions = re.findall(r'[😀-🙏]|:\)|:\(|:D|:P|XD|T_T|>_<', text)
        
        return list(set(emojis + text_emotions))
    
    def get_content_summary(self, content: str, max_length: int = 100) -> str:
        """
        获取内容摘要
        
        Args:
            content: 原始内容
            max_length: 最大长度
            
        Returns:
            内容摘要
        """
        if not content:
            return ""
        
        # 清理内容
        clean_content = self.clean_text(content)
        
        # 截取指定长度
        if len(clean_content) <= max_length:
            return clean_content
        
        return clean_content[:max_length] + "..."
    
    def analyze_content(self, content: str, images: List[str] = None) -> Dict[str, Any]:
        """
        综合分析内容
        
        Args:
            content: 文本内容
            images: 图片列表
            
        Returns:
            分析结果
        """
        images = images or []
        
        return {
            'content_length': len(content),
            'clean_content': self.clean_text(content),
            'summary': self.get_content_summary(content),
            'keywords': self.extract_keywords(content),
            'mentions': self.extract_mentions(content),
            'hashtags': self.extract_hashtags(content),
            'urls': self.extract_urls(content),
            'emotions': self.extract_emotions(content),
            'post_type': self.detect_post_type(content, images),
            'has_images': len(images) > 0,
            'image_count': len(images)
        }
