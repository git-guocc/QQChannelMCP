"""
内容筛选引擎
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.post import QQChannelPost
from ..models.filter_criteria import FilterCriteria
from ..core.exceptions import FilterError, handle_exception

logger = logging.getLogger(__name__)


class FilterEngine:
    """内容筛选引擎"""
    
    def __init__(self, ai_client=None):
        """
        初始化筛选引擎
        
        Args:
            ai_client: AI客户端，用于AI筛选
        """
        self.ai_client = ai_client
        
        # 预编译正则表达式以提高性能
        self._compiled_patterns = {}
    
    @handle_exception
    async def filter_posts(self, posts: List[QQChannelPost], criteria: FilterCriteria) -> List[QQChannelPost]:
        """
        根据条件筛选帖子
        
        Args:
            posts: 帖子列表
            criteria: 筛选条件
            
        Returns:
            筛选后的帖子列表
        """
        if not posts:
            return []
        
        if not criteria.has_any_filter():
            logger.info("无筛选条件，返回所有帖子")
            return posts
        
        logger.info(f"开始筛选 {len(posts)} 个帖子，条件: {criteria.get_summary()}")
        
        # 验证筛选条件
        validation_errors = criteria.validate()
        if validation_errors:
            raise FilterError(f"筛选条件无效: {'; '.join(validation_errors)}")
        
        filtered_posts = []
        
        # 逐个检查帖子
        for i, post in enumerate(posts):
            try:
                if await self._match_criteria(post, criteria):
                    filtered_posts.append(post)
                
                # 每处理100个帖子记录一次进度
                if (i + 1) % 100 == 0:
                    logger.debug(f"已处理 {i + 1}/{len(posts)} 个帖子")
                    
            except Exception as e:
                logger.warning(f"筛选第 {i+1} 个帖子时出错: {e}")
                continue
        
        # 排序
        if filtered_posts:
            filtered_posts = self._sort_posts(filtered_posts, criteria)
        
        # 限制结果数量
        if criteria.max_results and len(filtered_posts) > criteria.max_results:
            filtered_posts = filtered_posts[:criteria.max_results]
        
        logger.info(f"筛选完成: {len(filtered_posts)}/{len(posts)} 个帖子符合条件")
        return filtered_posts
    
    async def _match_criteria(self, post: QQChannelPost, criteria: FilterCriteria) -> bool:
        """检查帖子是否匹配筛选条件"""
        
        # 时间筛选
        if not self._check_time_filter(post, criteria):
            return False
        
        # 内容筛选
        if not self._check_content_filter(post, criteria):
            return False
        
        # 作者筛选
        if not self._check_author_filter(post, criteria):
            return False
        
        # 互动数据筛选
        if not self._check_interaction_filter(post, criteria):
            return False
        
        # 内容类型筛选
        if not self._check_type_filter(post, criteria):
            return False
        
        # 标签筛选
        if not self._check_tag_filter(post, criteria):
            return False
        
        # AI筛选（最后执行，因为开销较大）
        if criteria.ai_filter_prompt and not await self._check_ai_filter(post, criteria):
            return False
        
        return True
    
    def _check_time_filter(self, post: QQChannelPost, criteria: FilterCriteria) -> bool:
        """检查时间筛选条件"""
        if not criteria.time_range or not post.post_time:
            return True
        
        start_time, end_time = criteria.time_range
        return start_time <= post.post_time <= end_time
    
    def _check_content_filter(self, post: QQChannelPost, criteria: FilterCriteria) -> bool:
        """检查内容筛选条件"""
        content_text = f"{post.title or ''} {post.content}".lower().strip()
        
        # 关键词筛选
        if criteria.keywords:
            if not any(self._match_keyword(keyword, content_text) for keyword in criteria.keywords):
                return False
        
        # 排除关键词
        if criteria.exclude_keywords:
            if any(self._match_keyword(keyword, content_text) for keyword in criteria.exclude_keywords):
                return False
        
        # 内容长度筛选
        content_length = len(post.content)
        if criteria.content_length_min and content_length < criteria.content_length_min:
            return False
        if criteria.content_length_max and content_length > criteria.content_length_max:
            return False
        
        return True
    
    def _match_keyword(self, keyword: str, text: str) -> bool:
        """匹配关键词（支持正则表达式）"""
        keyword_lower = keyword.lower()
        
        # 如果关键词包含特殊字符，视为正则表达式
        if any(char in keyword for char in r'.*+?^${}[]|()\\'):
            try:
                pattern = self._compiled_patterns.get(keyword_lower)
                if not pattern:
                    pattern = re.compile(keyword_lower, re.IGNORECASE)
                    self._compiled_patterns[keyword_lower] = pattern
                return bool(pattern.search(text))
            except re.error:
                # 正则表达式无效，使用普通匹配
                return keyword_lower in text
        else:
            # 普通字符串匹配
            return keyword_lower in text
    
    def _check_author_filter(self, post: QQChannelPost, criteria: FilterCriteria) -> bool:
        """检查作者筛选条件"""
        # 指定作者
        if criteria.author_filter:
            if post.author_name not in criteria.author_filter:
                return False
        
        # 排除作者
        if criteria.exclude_authors:
            if post.author_name in criteria.exclude_authors:
                return False
        
        return True
    
    def _check_interaction_filter(self, post: QQChannelPost, criteria: FilterCriteria) -> bool:
        """检查互动数据筛选条件"""
        # 点赞数筛选
        if criteria.min_likes is not None and post.like_count < criteria.min_likes:
            return False
        if criteria.max_likes is not None and post.like_count > criteria.max_likes:
            return False
        
        # 评论数筛选
        if criteria.min_comments is not None and post.comment_count < criteria.min_comments:
            return False
        if criteria.max_comments is not None and post.comment_count > criteria.max_comments:
            return False
        
        # 分享数筛选
        if criteria.min_shares is not None and post.share_count < criteria.min_shares:
            return False
        
        # 浏览数筛选
        if criteria.min_views is not None and post.view_count < criteria.min_views:
            return False
        
        return True
    
    def _check_type_filter(self, post: QQChannelPost, criteria: FilterCriteria) -> bool:
        """检查内容类型筛选条件"""
        # 帖子类型筛选
        if criteria.post_types:
            if post.post_type not in criteria.post_types:
                return False
        
        # 图片筛选
        has_images = post.has_images()
        if criteria.has_images is not None:
            if criteria.has_images != has_images:
                return False
        
        # 图片数量筛选
        image_count = len(post.images)
        if criteria.min_images is not None and image_count < criteria.min_images:
            return False
        if criteria.max_images is not None and image_count > criteria.max_images:
            return False
        
        return True
    
    def _check_tag_filter(self, post: QQChannelPost, criteria: FilterCriteria) -> bool:
        """检查标签筛选条件"""
        post_tags = [tag.lower() for tag in post.tags]
        
        # 必须包含的标签
        if criteria.required_tags:
            required_tags_lower = [tag.lower() for tag in criteria.required_tags]
            if not all(tag in post_tags for tag in required_tags_lower):
                return False
        
        # 排除的标签
        if criteria.exclude_tags:
            exclude_tags_lower = [tag.lower() for tag in criteria.exclude_tags]
            if any(tag in post_tags for tag in exclude_tags_lower):
                return False
        
        return True
    
    async def _check_ai_filter(self, post: QQChannelPost, criteria: FilterCriteria) -> bool:
        """使用AI进行内容筛选"""
        if not self.ai_client:
            logger.warning("AI客户端未配置，跳过AI筛选")
            return True
        
        try:
            # 构建AI提示
            ai_prompt = self._build_ai_prompt(post, criteria.ai_filter_prompt)
            
            # 调用AI客户端
            response = await self._call_ai_client(ai_prompt)
            
            # 解析AI响应
            return self._parse_ai_response(response, criteria.ai_confidence_threshold)
            
        except Exception as e:
            logger.warning(f"AI筛选失败: {e}")
            return True  # 默认通过
    
    def _build_ai_prompt(self, post: QQChannelPost, user_prompt: str) -> str:
        """构建AI提示"""
        return f"""
请判断以下QQ频道帖子是否符合条件："{user_prompt}"

帖子信息：
- 标题：{post.title or '无'}
- 内容：{post.content[:500]}{'...' if len(post.content) > 500 else ''}
- 作者：{post.author_name}
- 发布时间：{post.post_time.strftime('%Y-%m-%d %H:%M') if post.post_time else '未知'}
- 点赞数：{post.like_count}
- 评论数：{post.comment_count}
- 是否有图片：{'是' if post.has_images() else '否'}
- 帖子类型：{post.post_type}

请回答：是 或 否
如果不确定，请回答：否
""".strip()
    
    async def _call_ai_client(self, prompt: str) -> str:
        """调用AI客户端"""
        # 这里需要根据实际使用的AI客户端进行调整
        # 示例实现（需要替换为实际的AI客户端调用）
        try:
            if hasattr(self.ai_client, 'generate'):
                response = await self.ai_client.generate(prompt)
            elif hasattr(self.ai_client, 'chat'):
                response = await self.ai_client.chat(prompt)
            else:
                # 简单的模拟实现
                response = "是"
            
            return response
            
        except Exception as e:
            logger.error(f"AI客户端调用失败: {e}")
            raise
    
    def _parse_ai_response(self, response: str, threshold: float) -> bool:
        """解析AI响应"""
        if not response:
            return False
        
        response_lower = response.lower().strip()
        
        # 简单的关键词匹配
        positive_keywords = ['是', 'yes', 'true', '符合', '匹配', '通过']
        negative_keywords = ['否', 'no', 'false', '不符合', '不匹配', '不通过']
        
        # 检查明确的肯定回答
        if any(keyword in response_lower for keyword in positive_keywords):
            return True
        
        # 检查明确的否定回答
        if any(keyword in response_lower for keyword in negative_keywords):
            return False
        
        # 如果无法确定，默认为False
        return False
    
    def _sort_posts(self, posts: List[QQChannelPost], criteria: FilterCriteria) -> List[QQChannelPost]:
        """排序帖子"""
        if not posts:
            return posts
        
        sort_key_map = {
            'time': lambda p: p.post_time or datetime.min,
            'likes': lambda p: p.like_count,
            'comments': lambda p: p.comment_count,
            'shares': lambda p: p.share_count,
            'views': lambda p: p.view_count,
            'author': lambda p: p.author_name,
            'content_length': lambda p: len(p.content)
        }
        
        sort_key = sort_key_map.get(criteria.sort_by, sort_key_map['time'])
        reverse = criteria.sort_order.lower() == 'desc'
        
        try:
            return sorted(posts, key=sort_key, reverse=reverse)
        except Exception as e:
            logger.warning(f"排序失败: {e}")
            return posts
    
    def get_filter_statistics(self, original_posts: List[QQChannelPost], 
                             filtered_posts: List[QQChannelPost],
                             criteria: FilterCriteria) -> Dict[str, Any]:
        """获取筛选统计信息"""
        return {
            'original_count': len(original_posts),
            'filtered_count': len(filtered_posts),
            'filter_rate': len(filtered_posts) / len(original_posts) if original_posts else 0,
            'criteria_summary': criteria.get_summary(),
            'filter_effects': {
                'total_likes': sum(p.like_count for p in filtered_posts),
                'total_comments': sum(p.comment_count for p in filtered_posts),
                'avg_likes': sum(p.like_count for p in filtered_posts) / len(filtered_posts) if filtered_posts else 0,
                'unique_authors': len(set(p.author_name for p in filtered_posts)),
                'post_types': self._count_post_types(filtered_posts),
                'time_range': self._get_time_range(filtered_posts)
            }
        }
    
    def _count_post_types(self, posts: List[QQChannelPost]) -> Dict[str, int]:
        """统计帖子类型"""
        type_counts = {}
        for post in posts:
            type_counts[post.post_type] = type_counts.get(post.post_type, 0) + 1
        return type_counts
    
    def _get_time_range(self, posts: List[QQChannelPost]) -> Dict[str, str]:
        """获取时间范围"""
        if not posts:
            return {}
        
        times = [p.post_time for p in posts if p.post_time]
        if not times:
            return {}
        
        return {
            'earliest': min(times).isoformat(),
            'latest': max(times).isoformat()
        }
