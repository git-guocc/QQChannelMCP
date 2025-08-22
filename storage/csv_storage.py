"""
CSV存储模块
"""

import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.post import QQChannelPost
from ..core.exceptions import StorageError, handle_exception

logger = logging.getLogger(__name__)


class CSVStorage:
    """CSV文件存储"""
    
    def __init__(self, storage_path: str = "data/posts.csv"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 定义CSV字段（中文表头，AI友好）
        self.fieldnames = [
            'post_id',           # 帖子ID
            'channel_name',      # 频道名称
            'author_name',       # 作者昵称
            'title',             # 帖子标题
            'content',           # 帖子内容
            'content_length',    # 内容长度
            'post_time',         # 发布时间
            'like_count',        # 点赞数
            'comment_count',     # 评论数
            'share_count',       # 分享数
            'view_count',        # 浏览数
            'images_count',      # 图片数量
            'image_urls',        # 图片链接（用分号分隔）
            'post_type',         # 帖子类型
            'post_url',          # 帖子链接
            'tags',              # 标签（用分号分隔）
            'collected_time'     # 采集时间
        ]
        
        # 中文表头映射（用于导出）
        self.chinese_headers = {
            'post_id': '帖子ID',
            'channel_name': '频道名称',
            'author_name': '作者昵称',
            'title': '帖子标题',
            'content': '帖子内容',
            'content_length': '内容长度',
            'post_time': '发布时间',
            'like_count': '点赞数',
            'comment_count': '评论数',
            'share_count': '分享数',
            'view_count': '浏览数',
            'images_count': '图片数量',
            'image_urls': '图片链接',
            'post_type': '帖子类型',
            'post_url': '帖子链接',
            'tags': '标签',
            'collected_time': '采集时间'
        }
    
    @handle_exception
    async def save_posts(self, posts: List[QQChannelPost], append: bool = False, use_chinese_headers: bool = True) -> bool:
        """
        保存帖子数据到CSV文件
        
        Args:
            posts: 帖子列表
            append: 是否追加模式
            use_chinese_headers: 是否使用中文表头
            
        Returns:
            是否保存成功
        """
        try:
            mode = 'a' if append and self.storage_path.exists() else 'w'
            write_header = mode == 'w' or not self.storage_path.exists()
            
            # 选择表头
            headers = [self.chinese_headers[field] for field in self.fieldnames] if use_chinese_headers else self.fieldnames
            
            with open(self.storage_path, mode, newline='', encoding='utf-8-sig') as f:  # 使用utf-8-sig支持Excel
                writer = csv.writer(f)
                
                # 写入表头
                if write_header:
                    writer.writerow(headers)
                
                # 写入数据
                for post in posts:
                    row = self._post_to_row(post)
                    writer.writerow(row)
            
            logger.info(f"成功保存 {len(posts)} 个帖子到 {self.storage_path} ({'追加' if append else '覆盖'}模式)")
            return True
            
        except Exception as e:
            raise StorageError(f"保存CSV数据失败: {str(e)}")
    
    def _post_to_row(self, post: QQChannelPost) -> List[str]:
        """将帖子对象转换为CSV行数据"""
        return [
            post.post_id,
            post.channel_name,
            post.author_name,
            post.title or '',
            post.content,
            str(len(post.content)),
            post.post_time.isoformat() if post.post_time else '',
            str(post.like_count),
            str(post.comment_count),
            str(post.share_count),
            str(post.view_count),
            str(len(post.images)),
            ';'.join(post.images),  # 用分号分隔多个图片URL
            post.post_type,
            post.post_url,
            ';'.join(post.tags),    # 用分号分隔多个标签
            post.collected_time.isoformat()
        ]
    
    @handle_exception
    async def load_posts(self, use_chinese_headers: bool = True) -> List[QQChannelPost]:
        """
        从CSV文件加载帖子数据
        
        Args:
            use_chinese_headers: 是否使用中文表头
            
        Returns:
            帖子列表
        """
        try:
            if not self.storage_path.exists():
                logger.warning(f"CSV文件不存在: {self.storage_path}")
                return []
            
            posts = []
            
            with open(self.storage_path, 'r', encoding='utf-8-sig') as f:
                # 检测表头类型
                first_line = f.readline().strip()
                f.seek(0)  # 重置文件指针
                
                # 判断是否为中文表头
                is_chinese = any(header in first_line for header in self.chinese_headers.values())
                
                reader = csv.DictReader(f)
                
                for row_data in reader:
                    try:
                        # 转换表头（如果需要）
                        if is_chinese:
                            row_data = self._convert_chinese_headers(row_data)
                        
                        post = self._row_to_post(row_data)
                        if post:
                            posts.append(post)
                            
                    except Exception as e:
                        logger.warning(f"解析CSV行数据失败: {e}")
                        continue
            
            logger.info(f"成功加载 {len(posts)} 个帖子从 {self.storage_path}")
            return posts
            
        except Exception as e:
            raise StorageError(f"加载CSV数据失败: {str(e)}")
    
    def _convert_chinese_headers(self, row_data: Dict[str, str]) -> Dict[str, str]:
        """转换中文表头为英文字段名"""
        # 创建中文到英文的映射
        chinese_to_english = {v: k for k, v in self.chinese_headers.items()}
        
        converted_data = {}
        for chinese_header, value in row_data.items():
            english_field = chinese_to_english.get(chinese_header, chinese_header)
            converted_data[english_field] = value
        
        return converted_data
    
    def _row_to_post(self, row_data: Dict[str, str]) -> Optional[QQChannelPost]:
        """将CSV行数据转换为帖子对象"""
        try:
            # 解析时间
            post_time = None
            if row_data.get('post_time'):
                from dateutil.parser import parse
                post_time = parse(row_data['post_time'])
            
            collected_time = datetime.now()
            if row_data.get('collected_time'):
                from dateutil.parser import parse
                collected_time = parse(row_data['collected_time'])
            
            # 解析图片URLs
            images = []
            if row_data.get('image_urls'):
                images = [url.strip() for url in row_data['image_urls'].split(';') if url.strip()]
            
            # 解析标签
            tags = []
            if row_data.get('tags'):
                tags = [tag.strip() for tag in row_data['tags'].split(';') if tag.strip()]
            
            # 创建帖子对象
            post = QQChannelPost(
                post_id=row_data.get('post_id', ''),
                channel_id='',  # CSV中可能没有channel_id
                channel_name=row_data.get('channel_name', ''),
                author_name=row_data.get('author_name', ''),
                title=row_data.get('title', ''),
                content=row_data.get('content', ''),
                images=images,
                post_time=post_time,
                like_count=int(row_data.get('like_count', 0) or 0),
                comment_count=int(row_data.get('comment_count', 0) or 0),
                share_count=int(row_data.get('share_count', 0) or 0),
                view_count=int(row_data.get('view_count', 0) or 0),
                post_type=row_data.get('post_type', 'text'),
                post_url=row_data.get('post_url', ''),
                tags=tags,
                collected_time=collected_time
            )
            
            return post
            
        except Exception as e:
            logger.error(f"转换行数据为帖子对象失败: {e}")
            return None
    
    @handle_exception
    async def append_posts(self, new_posts: List[QQChannelPost]) -> bool:
        """
        追加帖子数据
        
        Args:
            new_posts: 新的帖子列表
            
        Returns:
            是否追加成功
        """
        try:
            if not new_posts:
                logger.info("没有新帖子需要追加")
                return True
            
            # 如果文件不存在，直接保存
            if not self.storage_path.exists():
                return await self.save_posts(new_posts)
            
            # 加载现有数据进行去重
            existing_posts = await self.load_posts()
            existing_ids = {post.post_id for post in existing_posts}
            
            # 过滤重复数据
            unique_new_posts = [post for post in new_posts if post.post_id not in existing_ids]
            
            if not unique_new_posts:
                logger.info("没有新的唯一帖子需要追加")
                return True
            
            # 追加新数据
            return await self.save_posts(unique_new_posts, append=True)
            
        except Exception as e:
            raise StorageError(f"追加CSV数据失败: {str(e)}")
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            if not self.storage_path.exists():
                return {
                    'exists': False,
                    'path': str(self.storage_path)
                }
            
            stat = self.storage_path.stat()
            
            # 计算行数
            line_count = 0
            with open(self.storage_path, 'r', encoding='utf-8-sig') as f:
                line_count = sum(1 for _ in f)
            
            record_count = max(0, line_count - 1)  # 减去表头行
            
            return {
                'exists': True,
                'path': str(self.storage_path),
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'record_count': record_count,
                'line_count': line_count
            }
            
        except Exception as e:
            logger.error(f"获取CSV存储统计失败: {e}")
            return {
                'exists': False,
                'error': str(e)
            }
    
    @handle_exception
    async def export_for_analysis(self, output_path: str, include_content: bool = True) -> bool:
        """
        导出用于数据分析的CSV文件
        
        Args:
            output_path: 输出路径
            include_content: 是否包含完整内容（可能很长）
            
        Returns:
            是否导出成功
        """
        try:
            posts = await self.load_posts()
            if not posts:
                logger.warning("没有数据可导出")
                return False
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 分析用字段
            analysis_fields = [
                'post_id', 'channel_name', 'author_name', 'title',
                'content_length', 'post_time', 'like_count', 'comment_count',
                'share_count', 'images_count', 'post_type', 'collected_time'
            ]
            
            if include_content:
                analysis_fields.insert(4, 'content')  # 在content_length之前插入content
            
            # 中文表头
            analysis_headers = [self.chinese_headers[field] for field in analysis_fields]
            
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(analysis_headers)
                
                for post in posts:
                    row = []
                    for field in analysis_fields:
                        if field == 'post_id':
                            row.append(post.post_id)
                        elif field == 'channel_name':
                            row.append(post.channel_name)
                        elif field == 'author_name':
                            row.append(post.author_name)
                        elif field == 'title':
                            row.append(post.title or '')
                        elif field == 'content':
                            row.append(post.content)
                        elif field == 'content_length':
                            row.append(len(post.content))
                        elif field == 'post_time':
                            row.append(post.post_time.isoformat() if post.post_time else '')
                        elif field == 'like_count':
                            row.append(post.like_count)
                        elif field == 'comment_count':
                            row.append(post.comment_count)
                        elif field == 'share_count':
                            row.append(post.share_count)
                        elif field == 'images_count':
                            row.append(len(post.images))
                        elif field == 'post_type':
                            row.append(post.post_type)
                        elif field == 'collected_time':
                            row.append(post.collected_time.isoformat())
                    
                    writer.writerow(row)
            
            logger.info(f"成功导出分析用CSV文件: {output_path}")
            return True
            
        except Exception as e:
            raise StorageError(f"导出分析用CSV失败: {str(e)}")
    
    @handle_exception 
    async def create_summary_report(self, output_path: str) -> bool:
        """
        创建数据摘要报告
        
        Args:
            output_path: 输出路径
            
        Returns:
            是否创建成功
        """
        try:
            posts = await self.load_posts()
            if not posts:
                logger.warning("没有数据可分析")
                return False
            
            # 统计分析
            total_posts = len(posts)
            total_likes = sum(post.like_count for post in posts)
            total_comments = sum(post.comment_count for post in posts)
            unique_authors = len(set(post.author_name for post in posts))
            
            # 按类型统计
            type_counts = {}
            for post in posts:
                type_counts[post.post_type] = type_counts.get(post.post_type, 0) + 1
            
            # 按频道统计
            channel_counts = {}
            for post in posts:
                channel_counts[post.channel_name] = channel_counts.get(post.channel_name, 0) + 1
            
            # 热门作者
            author_likes = {}
            for post in posts:
                author_likes[post.author_name] = author_likes.get(post.author_name, 0) + post.like_count
            
            top_authors = sorted(author_likes.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # 创建摘要报告
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # 基础统计
                writer.writerow(['数据摘要报告', ''])
                writer.writerow(['生成时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([''])
                
                writer.writerow(['基础统计', ''])
                writer.writerow(['总帖子数', total_posts])
                writer.writerow(['总点赞数', total_likes])
                writer.writerow(['总评论数', total_comments])
                writer.writerow(['独立作者数', unique_authors])
                writer.writerow(['平均点赞数', round(total_likes / total_posts, 2) if total_posts > 0 else 0])
                writer.writerow([''])
                
                # 按类型统计
                writer.writerow(['帖子类型分布', ''])
                for post_type, count in type_counts.items():
                    writer.writerow([post_type, count])
                writer.writerow([''])
                
                # 按频道统计
                writer.writerow(['频道分布', ''])
                for channel, count in sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    writer.writerow([channel, count])
                writer.writerow([''])
                
                # 热门作者
                writer.writerow(['热门作者Top10', ''])
                writer.writerow(['作者', '总点赞数'])
                for author, likes in top_authors:
                    writer.writerow([author, likes])
            
            logger.info(f"成功创建摘要报告: {output_path}")
            return True
            
        except Exception as e:
            raise StorageError(f"创建摘要报告失败: {str(e)}")
