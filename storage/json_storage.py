"""
JSON存储模块
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.post import QQChannelPost, PostCollection
from ..models.channel import QQChannel
from ..core.exceptions import StorageError, handle_exception

logger = logging.getLogger(__name__)


class JSONStorage:
    """JSON文件存储"""
    
    def __init__(self, storage_path: str = "data/posts.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
    
    @handle_exception
    async def save_posts(self, posts: List[QQChannelPost], metadata: Optional[Dict] = None) -> bool:
        """
        保存帖子数据到JSON文件
        
        Args:
            posts: 帖子列表
            metadata: 额外的元数据
            
        Returns:
            是否保存成功
        """
        try:
            # 创建帖子集合
            collection = PostCollection(
                posts=posts,
                channel_name=posts[0].channel_name if posts else "",
                collected_time=datetime.now(),
                total_count=len(posts),
                metadata=metadata or {}
            )
            
            # 转换为字典
            data = collection.to_dict()
            
            # 保存到文件
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存 {len(posts)} 个帖子到 {self.storage_path}")
            return True
            
        except Exception as e:
            raise StorageError(f"保存帖子数据失败: {str(e)}")
    
    @handle_exception
    async def load_posts(self) -> List[QQChannelPost]:
        """
        从JSON文件加载帖子数据
        
        Returns:
            帖子列表
        """
        try:
            if not self.storage_path.exists():
                logger.warning(f"存储文件不存在: {self.storage_path}")
                return []
            
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查数据格式
            if isinstance(data, dict) and 'posts' in data:
                # 新格式：PostCollection
                collection = PostCollection.from_dict(data)
                posts = collection.posts
            elif isinstance(data, list):
                # 旧格式：直接的帖子列表
                posts = [QQChannelPost.from_dict(post_data) for post_data in data]
            else:
                raise StorageError("无效的JSON数据格式")
            
            logger.info(f"成功加载 {len(posts)} 个帖子从 {self.storage_path}")
            return posts
            
        except Exception as e:
            raise StorageError(f"加载帖子数据失败: {str(e)}")
    
    @handle_exception
    async def append_posts(self, new_posts: List[QQChannelPost]) -> bool:
        """
        追加帖子数据到现有文件
        
        Args:
            new_posts: 新的帖子列表
            
        Returns:
            是否追加成功
        """
        try:
            # 加载现有数据
            existing_posts = await self.load_posts()
            
            # 去重处理（基于post_id）
            existing_ids = {post.post_id for post in existing_posts}
            unique_new_posts = [post for post in new_posts if post.post_id not in existing_ids]
            
            if not unique_new_posts:
                logger.info("没有新的帖子需要追加")
                return True
            
            # 合并数据
            all_posts = existing_posts + unique_new_posts
            
            # 保存合并后的数据
            metadata = {
                'last_append_time': datetime.now().isoformat(),
                'appended_count': len(unique_new_posts),
                'total_count': len(all_posts)
            }
            
            return await self.save_posts(all_posts, metadata)
            
        except Exception as e:
            raise StorageError(f"追加帖子数据失败: {str(e)}")
    
    @handle_exception
    async def save_channel_info(self, channel: QQChannel) -> bool:
        """
        保存频道信息
        
        Args:
            channel: 频道对象
            
        Returns:
            是否保存成功
        """
        try:
            channel_path = self.storage_path.parent / f"channel_{channel.channel_id}.json"
            
            with open(channel_path, 'w', encoding='utf-8') as f:
                json.dump(channel.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存频道信息到 {channel_path}")
            return True
            
        except Exception as e:
            raise StorageError(f"保存频道信息失败: {str(e)}")
    
    @handle_exception
    async def load_channel_info(self, channel_id: str) -> Optional[QQChannel]:
        """
        加载频道信息
        
        Args:
            channel_id: 频道ID
            
        Returns:
            频道对象或None
        """
        try:
            channel_path = self.storage_path.parent / f"channel_{channel_id}.json"
            
            if not channel_path.exists():
                return None
            
            with open(channel_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return QQChannel.from_dict(data)
            
        except Exception as e:
            logger.error(f"加载频道信息失败: {e}")
            return None
    
    @handle_exception
    async def export_to_format(self, output_path: str, format_type: str = "json") -> bool:
        """
        导出数据到指定格式
        
        Args:
            output_path: 输出路径
            format_type: 导出格式 (json/csv)
            
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
            
            if format_type.lower() == "json":
                return await self._export_to_json(posts, output_path)
            elif format_type.lower() == "csv":
                return await self._export_to_csv(posts, output_path)
            else:
                raise StorageError(f"不支持的导出格式: {format_type}")
                
        except Exception as e:
            raise StorageError(f"导出数据失败: {str(e)}")
    
    async def _export_to_json(self, posts: List[QQChannelPost], output_path: Path) -> bool:
        """导出为JSON格式"""
        data = {
            'export_time': datetime.now().isoformat(),
            'total_count': len(posts),
            'posts': [post.to_dict() for post in posts]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"成功导出 {len(posts)} 个帖子到 {output_path}")
        return True
    
    async def _export_to_csv(self, posts: List[QQChannelPost], output_path: Path) -> bool:
        """导出为CSV格式"""
        import csv
        
        if not posts:
            return False
        
        # 定义CSV字段
        fieldnames = [
            'post_id', 'channel_name', 'author_name', 'title', 'content',
            'post_time', 'like_count', 'comment_count', 'share_count',
            'images_count', 'post_type', 'post_url', 'collected_time'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for post in posts:
                row = {
                    'post_id': post.post_id,
                    'channel_name': post.channel_name,
                    'author_name': post.author_name,
                    'title': post.title or '',
                    'content': post.content,
                    'post_time': post.post_time.isoformat() if post.post_time else '',
                    'like_count': post.like_count,
                    'comment_count': post.comment_count,
                    'share_count': post.share_count,
                    'images_count': len(post.images),
                    'post_type': post.post_type,
                    'post_url': post.post_url,
                    'collected_time': post.collected_time.isoformat()
                }
                writer.writerow(row)
        
        logger.info(f"成功导出 {len(posts)} 个帖子到 {output_path}")
        return True
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        try:
            if not self.storage_path.exists():
                return {
                    'exists': False,
                    'path': str(self.storage_path)
                }
            
            stat = self.storage_path.stat()
            
            # 尝试获取记录数量
            try:
                posts = []
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, dict) and 'posts' in data:
                    posts = data['posts']
                elif isinstance(data, list):
                    posts = data
                
                record_count = len(posts)
                
            except Exception:
                record_count = 0
            
            return {
                'exists': True,
                'path': str(self.storage_path),
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'record_count': record_count
            }
            
        except Exception as e:
            logger.error(f"获取存储信息失败: {e}")
            return {
                'exists': False,
                'error': str(e)
            }
    
    @handle_exception
    async def backup_data(self, backup_path: Optional[str] = None) -> str:
        """
        备份数据
        
        Args:
            backup_path: 备份路径，如果不指定则自动生成
            
        Returns:
            备份文件路径
        """
        try:
            if not self.storage_path.exists():
                raise StorageError("源文件不存在，无法备份")
            
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"backup_{timestamp}_{self.storage_path.name}"
                backup_path = self.storage_path.parent / "backups" / backup_filename
            else:
                backup_path = Path(backup_path)
            
            # 确保备份目录存在
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 复制文件
            import shutil
            shutil.copy2(self.storage_path, backup_path)
            
            logger.info(f"数据备份成功: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            raise StorageError(f"数据备份失败: {str(e)}")
    
    @handle_exception
    async def restore_data(self, backup_path: str) -> bool:
        """
        恢复数据
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            是否恢复成功
        """
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                raise StorageError(f"备份文件不存在: {backup_path}")
            
            # 验证备份文件格式
            with open(backup_path, 'r', encoding='utf-8') as f:
                json.load(f)  # 验证JSON格式
            
            # 备份当前文件（如果存在）
            if self.storage_path.exists():
                await self.backup_data()
            
            # 恢复数据
            import shutil
            shutil.copy2(backup_path, self.storage_path)
            
            logger.info(f"数据恢复成功: {backup_path} -> {self.storage_path}")
            return True
            
        except Exception as e:
            raise StorageError(f"数据恢复失败: {str(e)}")
