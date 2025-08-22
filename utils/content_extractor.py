"""
内容提取工具
"""

import re
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ContentExtractor:
    """内容提取器"""
    
    def __init__(self):
        # 常用的文本清理模式
        self.clean_patterns = [
            (r'\s+', ' '),  # 多个空白字符合并为一个空格
            (r'[\r\n]+', '\n'),  # 多个换行符合并
            (r'[^\w\s\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef.,!?;:()[\]{}"""''""…—-]', ''),  # 移除特殊字符
        ]
        
        # 表情符号模式
        self.emoji_pattern = re.compile(
            r'[\U0001F600-\U0001F64F'  # 表情符号
            r'\U0001F300-\U0001F5FF'  # 各种符号
            r'\U0001F680-\U0001F6FF'  # 交通和地图符号
            r'\U0001F1E0-\U0001F1FF'  # 国旗
            r'\U00002600-\U000027BF'  # 其他符号
            r'\U0001f900-\U0001f9ff'  # 补充符号
            r'\U0001f600-\U0001f64f]+'  # 表情符号（重复）
        )
    
    def extract_text_from_element(self, element) -> str:
        """
        从HTML元素中提取纯文本
        
        Args:
            element: HTML元素对象
            
        Returns:
            提取的文本
        """
        try:
            if hasattr(element, 'get_text'):
                # BeautifulSoup元素
                text = element.get_text(separator=' ', strip=True)
            elif hasattr(element, 'text'):
                # Selenium元素
                text = element.text
            else:
                # 字符串
                text = str(element)
            
            return self.clean_text(text)
            
        except Exception as e:
            logger.error(f"提取文本失败: {e}")
            return ""
    
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
        
        try:
            # 应用清理模式
            for pattern, replacement in self.clean_patterns:
                text = re.sub(pattern, replacement, text)
            
            # 移除首尾空白
            text = text.strip()
            
            return text
            
        except Exception as e:
            logger.error(f"文本清理失败: {e}")
            return text
    
    def extract_urls(self, text: str) -> List[str]:
        """
        提取文本中的URL
        
        Args:
            text: 文本内容
            
        Returns:
            URL列表
        """
        if not text:
            return []
        
        try:
            # URL正则表达式
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, text)
            
            # 去重并过滤
            unique_urls = []
            for url in urls:
                if url not in unique_urls and self._is_valid_url(url):
                    unique_urls.append(url)
            
            return unique_urls
            
        except Exception as e:
            logger.error(f"提取URL失败: {e}")
            return []
    
    def _is_valid_url(self, url: str) -> bool:
        """检查URL是否有效"""
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
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
        
        try:
            # 匹配@用户名模式（支持中文用户名）
            mention_pattern = r'@([a-zA-Z0-9_\u4e00-\u9fa5]{1,20})'
            mentions = re.findall(mention_pattern, text)
            
            # 去重
            return list(set(mentions))
            
        except Exception as e:
            logger.error(f"提取@提及失败: {e}")
            return []
    
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
        
        try:
            # 匹配#话题#模式
            hashtag_patterns = [
                r'#([^#\s]{1,30})#',  # #话题#
                r'#([^#\s]{1,30})\s',  # #话题 (后面跟空格)
                r'#([^#\s]{1,30})$',   # #话题 (在行末)
            ]
            
            hashtags = []
            for pattern in hashtag_patterns:
                matches = re.findall(pattern, text)
                hashtags.extend(matches)
            
            # 去重并过滤
            unique_hashtags = []
            for tag in hashtags:
                tag = tag.strip()
                if tag and tag not in unique_hashtags and len(tag) > 1:
                    unique_hashtags.append(tag)
            
            return unique_hashtags
            
        except Exception as e:
            logger.error(f"提取话题标签失败: {e}")
            return []
    
    def extract_emojis(self, text: str) -> List[str]:
        """
        提取表情符号
        
        Args:
            text: 文本内容
            
        Returns:
            表情符号列表
        """
        if not text:
            return []
        
        try:
            # 提取emoji
            emojis = self.emoji_pattern.findall(text)
            
            # 提取文字表情
            text_emoji_pattern = r'[:;8][-o\*\']?[\)\]\(\[dDpP/\:\\}{@\|]|[<>]?[:;=8][-o\*\']?[3DOPp@$\*\\\|/\(\)\[\]{}]+'
            text_emojis = re.findall(text_emoji_pattern, text)
            
            # 合并去重
            all_emojis = list(set(emojis + text_emojis))
            
            return all_emojis
            
        except Exception as e:
            logger.error(f"提取表情符号失败: {e}")
            return []
    
    def extract_keywords(self, text: str, min_length: int = 2, max_count: int = 20) -> List[str]:
        """
        提取关键词
        
        Args:
            text: 文本内容
            min_length: 最小词长度
            max_count: 最大关键词数量
            
        Returns:
            关键词列表
        """
        if not text:
            return []
        
        try:
            # 简单的关键词提取（可以后续集成jieba等分词工具）
            
            # 移除标点符号
            clean_text = re.sub(r'[^\w\s\u4e00-\u9fa5]', ' ', text)
            
            # 分割单词
            words = clean_text.split()
            
            # 过滤停用词和短词
            stop_words = {
                '的', '了', '是', '在', '我', '你', '他', '她', '它', '和', '与', '或', 
                '但', '而', '也', '都', '很', '更', '最', '就', '还', '只', '又', 
                '已', '被', '把', '从', '到', '对', '为', '以', '之', '上', '下',
                'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
                'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
                'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have'
            }
            
            keywords = []
            for word in words:
                word = word.strip().lower()
                if (len(word) >= min_length and 
                    word not in stop_words and 
                    word not in keywords and
                    not word.isdigit()):
                    keywords.append(word)
            
            return keywords[:max_count]
            
        except Exception as e:
            logger.error(f"提取关键词失败: {e}")
            return []
    
    def extract_numbers(self, text: str) -> List[Dict[str, Any]]:
        """
        提取数字信息
        
        Args:
            text: 文本内容
            
        Returns:
            数字信息列表
        """
        if not text:
            return []
        
        try:
            # 匹配各种数字格式
            number_patterns = [
                (r'(\d+(?:\.\d+)?)\s*[wW万]', lambda m: {'value': float(m.group(1)) * 10000, 'unit': '万', 'original': m.group(0)}),
                (r'(\d+(?:\.\d+)?)\s*[kK千]', lambda m: {'value': float(m.group(1)) * 1000, 'unit': '千', 'original': m.group(0)}),
                (r'(\d+(?:\.\d+)?)\s*[百]', lambda m: {'value': float(m.group(1)) * 100, 'unit': '百', 'original': m.group(0)}),
                (r'(\d+(?:,\d{3})*(?:\.\d+)?)', lambda m: {'value': float(m.group(1).replace(',', '')), 'unit': '', 'original': m.group(0)}),
            ]
            
            numbers = []
            for pattern, converter in number_patterns:
                for match in re.finditer(pattern, text):
                    try:
                        number_info = converter(match)
                        numbers.append(number_info)
                    except (ValueError, AttributeError):
                        continue
            
            return numbers
            
        except Exception as e:
            logger.error(f"提取数字失败: {e}")
            return []
    
    def extract_time_expressions(self, text: str) -> List[str]:
        """
        提取时间表达式
        
        Args:
            text: 文本内容
            
        Returns:
            时间表达式列表
        """
        if not text:
            return []
        
        try:
            time_patterns = [
                r'\d{4}年\d{1,2}月\d{1,2}日',  # 2024年1月1日
                r'\d{1,2}月\d{1,2}日',          # 1月1日
                r'\d{1,2}:\d{2}',               # 14:30
                r'\d+分钟前',                    # 30分钟前
                r'\d+小时前',                    # 2小时前
                r'\d+天前',                      # 3天前
                r'昨天|前天|今天|明天|后天',        # 相对时间
                r'刚刚|刚才',                    # 即时时间
                r'\d{4}-\d{1,2}-\d{1,2}',       # 2024-01-01
            ]
            
            time_expressions = []
            for pattern in time_patterns:
                matches = re.findall(pattern, text)
                time_expressions.extend(matches)
            
            return list(set(time_expressions))
            
        except Exception as e:
            logger.error(f"提取时间表达式失败: {e}")
            return []
    
    def analyze_content_structure(self, text: str) -> Dict[str, Any]:
        """
        分析内容结构
        
        Args:
            text: 文本内容
            
        Returns:
            内容结构分析结果
        """
        if not text:
            return {}
        
        try:
            # 基本统计
            char_count = len(text)
            word_count = len(text.split())
            line_count = len(text.split('\n'))
            
            # 内容特征
            has_urls = bool(self.extract_urls(text))
            has_mentions = bool(self.extract_mentions(text))
            has_hashtags = bool(self.extract_hashtags(text))
            has_emojis = bool(self.extract_emojis(text))
            has_numbers = bool(self.extract_numbers(text))
            
            # 语言检测（简单实现）
            chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
            english_chars = len(re.findall(r'[a-zA-Z]', text))
            
            if chinese_chars > english_chars:
                primary_language = 'chinese'
            elif english_chars > 0:
                primary_language = 'english'
            else:
                primary_language = 'unknown'
            
            return {
                'char_count': char_count,
                'word_count': word_count,
                'line_count': line_count,
                'has_urls': has_urls,
                'has_mentions': has_mentions,
                'has_hashtags': has_hashtags,
                'has_emojis': has_emojis,
                'has_numbers': has_numbers,
                'chinese_char_count': chinese_chars,
                'english_char_count': english_chars,
                'primary_language': primary_language,
                'chinese_ratio': chinese_chars / char_count if char_count > 0 else 0,
                'english_ratio': english_chars / char_count if char_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"分析内容结构失败: {e}")
            return {'error': str(e)}
    
    def extract_all_features(self, text: str) -> Dict[str, Any]:
        """
        提取所有内容特征
        
        Args:
            text: 文本内容
            
        Returns:
            完整的内容特征字典
        """
        try:
            return {
                'clean_text': self.clean_text(text),
                'urls': self.extract_urls(text),
                'mentions': self.extract_mentions(text),
                'hashtags': self.extract_hashtags(text),
                'emojis': self.extract_emojis(text),
                'keywords': self.extract_keywords(text),
                'numbers': self.extract_numbers(text),
                'time_expressions': self.extract_time_expressions(text),
                'structure': self.analyze_content_structure(text)
            }
            
        except Exception as e:
            logger.error(f"提取所有特征失败: {e}")
            return {'error': str(e)}
