"""
筛选条件数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import json


@dataclass
class FilterCriteria:
    """筛选条件模型"""
    
    # 时间筛选
    time_range: Optional[Tuple[datetime, datetime]] = None  # 时间范围 (start, end)
    time_range_days: Optional[int] = None  # 最近N天
    
    # 内容筛选
    keywords: List[str] = field(default_factory=list)  # 关键词列表
    exclude_keywords: List[str] = field(default_factory=list)  # 排除关键词
    content_length_min: Optional[int] = None  # 最小内容长度
    content_length_max: Optional[int] = None  # 最大内容长度
    
    # 作者筛选
    author_filter: List[str] = field(default_factory=list)  # 指定作者
    exclude_authors: List[str] = field(default_factory=list)  # 排除作者
    
    # 互动数据筛选
    min_likes: Optional[int] = None     # 最小点赞数
    max_likes: Optional[int] = None     # 最大点赞数
    min_comments: Optional[int] = None  # 最小评论数
    max_comments: Optional[int] = None  # 最大评论数
    min_shares: Optional[int] = None    # 最小分享数
    min_views: Optional[int] = None     # 最小浏览数
    
    # 内容类型筛选
    post_types: List[str] = field(default_factory=list)  # 帖子类型筛选 ['text', 'image', 'video']
    has_images: Optional[bool] = None   # 是否包含图片
    min_images: Optional[int] = None    # 最小图片数量
    max_images: Optional[int] = None    # 最大图片数量
    
    # 标签筛选
    required_tags: List[str] = field(default_factory=list)  # 必须包含的标签
    exclude_tags: List[str] = field(default_factory=list)   # 排除的标签
    
    # AI筛选
    ai_filter_prompt: Optional[str] = None  # AI筛选提示词
    ai_confidence_threshold: float = 0.7    # AI筛选置信度阈值
    
    # 排序选项
    sort_by: str = "time"  # 排序字段: time, likes, comments, shares
    sort_order: str = "desc"  # 排序顺序: asc, desc
    
    # 数量限制
    max_results: Optional[int] = None  # 最大结果数量
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果指定了最近N天，自动设置时间范围
        if self.time_range_days and not self.time_range:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=self.time_range_days)
            self.time_range = (start_time, end_time)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = {
            'time_range_days': self.time_range_days,
            'keywords': self.keywords,
            'exclude_keywords': self.exclude_keywords,
            'content_length_min': self.content_length_min,
            'content_length_max': self.content_length_max,
            'author_filter': self.author_filter,
            'exclude_authors': self.exclude_authors,
            'min_likes': self.min_likes,
            'max_likes': self.max_likes,
            'min_comments': self.min_comments,
            'max_comments': self.max_comments,
            'min_shares': self.min_shares,
            'min_views': self.min_views,
            'post_types': self.post_types,
            'has_images': self.has_images,
            'min_images': self.min_images,
            'max_images': self.max_images,
            'required_tags': self.required_tags,
            'exclude_tags': self.exclude_tags,
            'ai_filter_prompt': self.ai_filter_prompt,
            'ai_confidence_threshold': self.ai_confidence_threshold,
            'sort_by': self.sort_by,
            'sort_order': self.sort_order,
            'max_results': self.max_results
        }
        
        # 处理时间范围
        if self.time_range:
            data['time_range'] = [
                self.time_range[0].isoformat(),
                self.time_range[1].isoformat()
            ]
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FilterCriteria":
        """从字典创建实例"""
        # 处理时间范围
        if data.get('time_range'):
            from dateutil.parser import parse
            start_time = parse(data['time_range'][0])
            end_time = parse(data['time_range'][1])
            data['time_range'] = (start_time, end_time)
        
        # 处理列表字段
        list_fields = [
            'keywords', 'exclude_keywords', 'author_filter', 'exclude_authors',
            'post_types', 'required_tags', 'exclude_tags'
        ]
        for field in list_fields:
            data[field] = data.get(field, [])
        
        return cls(**data)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "FilterCriteria":
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def add_keyword(self, keyword: str) -> None:
        """添加关键词"""
        if keyword and keyword not in self.keywords:
            self.keywords.append(keyword)
    
    def add_author(self, author: str) -> None:
        """添加作者筛选"""
        if author and author not in self.author_filter:
            self.author_filter.append(author)
    
    def add_post_type(self, post_type: str) -> None:
        """添加帖子类型"""
        if post_type and post_type not in self.post_types:
            self.post_types.append(post_type)
    
    def set_time_range_days(self, days: int) -> None:
        """设置最近N天"""
        self.time_range_days = days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        self.time_range = (start_time, end_time)
    
    def set_likes_range(self, min_likes: Optional[int] = None, max_likes: Optional[int] = None) -> None:
        """设置点赞数范围"""
        if min_likes is not None:
            self.min_likes = min_likes
        if max_likes is not None:
            self.max_likes = max_likes
    
    def has_any_filter(self) -> bool:
        """检查是否有任何筛选条件"""
        return any([
            self.time_range,
            self.keywords,
            self.author_filter,
            self.min_likes is not None,
            self.min_comments is not None,
            self.post_types,
            self.has_images is not None,
            self.required_tags,
            self.ai_filter_prompt
        ])
    
    def get_summary(self) -> str:
        """获取筛选条件摘要"""
        conditions = []
        
        if self.time_range_days:
            conditions.append(f"最近{self.time_range_days}天")
        
        if self.keywords:
            conditions.append(f"关键词:{','.join(self.keywords[:3])}")
        
        if self.author_filter:
            conditions.append(f"作者:{','.join(self.author_filter[:3])}")
        
        if self.min_likes:
            conditions.append(f"点赞≥{self.min_likes}")
        
        if self.post_types:
            conditions.append(f"类型:{','.join(self.post_types)}")
        
        if self.has_images is not None:
            conditions.append("含图片" if self.has_images else "无图片")
        
        if self.ai_filter_prompt:
            conditions.append("AI筛选")
        
        return " | ".join(conditions) if conditions else "无筛选条件"
    
    def validate(self) -> List[str]:
        """验证筛选条件"""
        errors = []
        
        # 验证数值范围
        if self.min_likes is not None and self.max_likes is not None:
            if self.min_likes > self.max_likes:
                errors.append("最小点赞数不能大于最大点赞数")
        
        if self.content_length_min is not None and self.content_length_max is not None:
            if self.content_length_min > self.content_length_max:
                errors.append("最小内容长度不能大于最大内容长度")
        
        # 验证时间范围
        if self.time_range:
            start_time, end_time = self.time_range
            if start_time > end_time:
                errors.append("开始时间不能晚于结束时间")
        
        # 验证帖子类型
        valid_types = {'text', 'image', 'video'}
        for post_type in self.post_types:
            if post_type not in valid_types:
                errors.append(f"无效的帖子类型: {post_type}")
        
        return errors
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"FilterCriteria({self.get_summary()})"


@dataclass
class QuickFilters:
    """快速筛选条件预设"""
    
    @staticmethod
    def recent_hot_posts(days: int = 7, min_likes: int = 50) -> FilterCriteria:
        """最近热门帖子"""
        return FilterCriteria(
            time_range_days=days,
            min_likes=min_likes,
            sort_by="likes",
            sort_order="desc"
        )
    
    @staticmethod
    def recent_image_posts(days: int = 3) -> FilterCriteria:
        """最近图片帖子"""
        return FilterCriteria(
            time_range_days=days,
            has_images=True,
            post_types=["image"],
            sort_by="time",
            sort_order="desc"
        )
    
    @staticmethod
    def author_posts(author_name: str, days: int = 30) -> FilterCriteria:
        """指定作者帖子"""
        return FilterCriteria(
            time_range_days=days,
            author_filter=[author_name],
            sort_by="time",
            sort_order="desc"
        )
    
    @staticmethod
    def keyword_search(keywords: List[str], days: int = 14) -> FilterCriteria:
        """关键词搜索"""
        return FilterCriteria(
            time_range_days=days,
            keywords=keywords,
            sort_by="likes",
            sort_order="desc"
        )
    
    @staticmethod
    def high_engagement(min_likes: int = 100, min_comments: int = 10) -> FilterCriteria:
        """高互动帖子"""
        return FilterCriteria(
            min_likes=min_likes,
            min_comments=min_comments,
            sort_by="likes",
            sort_order="desc"
        )
