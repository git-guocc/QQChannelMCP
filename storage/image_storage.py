"""
图片存储管理模块
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..core.exceptions import StorageError, handle_exception

logger = logging.getLogger(__name__)


class ImageStorage:
    """图片存储管理器"""
    
    def __init__(self, images_dir: str = "data/images", metadata_file: str = "data/image_metadata.json"):
        self.images_dir = Path(images_dir)
        self.metadata_file = Path(metadata_file)
        
        # 确保目录存在
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 图片元数据缓存
        self._metadata_cache = {}
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """加载图片元数据"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self._metadata_cache = json.load(f)
        except Exception as e:
            logger.warning(f"加载图片元数据失败: {e}")
            self._metadata_cache = {}
    
    def _save_metadata(self) -> None:
        """保存图片元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存图片元数据失败: {e}")
    
    @handle_exception
    async def register_image(self, local_path: str, original_url: str, 
                           post_id: str = None, metadata: Dict = None) -> bool:
        """
        注册图片信息
        
        Args:
            local_path: 本地文件路径
            original_url: 原始URL
            post_id: 关联的帖子ID
            metadata: 额外元数据
            
        Returns:
            是否注册成功
        """
        try:
            local_path = Path(local_path)
            
            if not local_path.exists():
                raise StorageError(f"图片文件不存在: {local_path}")
            
            # 获取文件信息
            stat = local_path.stat()
            
            # 创建图片记录
            image_record = {
                'local_path': str(local_path),
                'original_url': original_url,
                'post_id': post_id,
                'file_size': stat.st_size,
                'file_size_mb': round(stat.st_size / (1024 * 1024), 3),
                'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'registered_time': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # 使用文件名作为键
            file_key = local_path.name
            self._metadata_cache[file_key] = image_record
            
            # 保存元数据
            self._save_metadata()
            
            logger.debug(f"注册图片: {file_key}")
            return True
            
        except Exception as e:
            raise StorageError(f"注册图片失败: {str(e)}")
    
    @handle_exception
    async def register_images_batch(self, image_records: List[Dict[str, Any]]) -> int:
        """
        批量注册图片
        
        Args:
            image_records: 图片记录列表，每个记录包含local_path, original_url等
            
        Returns:
            成功注册的数量
        """
        success_count = 0
        
        for record in image_records:
            try:
                await self.register_image(
                    local_path=record.get('local_path'),
                    original_url=record.get('original_url'),
                    post_id=record.get('post_id'),
                    metadata=record.get('metadata')
                )
                success_count += 1
            except Exception as e:
                logger.warning(f"注册图片失败: {e}")
                continue
        
        logger.info(f"批量注册图片完成: {success_count}/{len(image_records)}")
        return success_count
    
    def get_image_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        获取图片信息
        
        Args:
            filename: 文件名
            
        Returns:
            图片信息字典或None
        """
        return self._metadata_cache.get(filename)
    
    def find_images_by_post(self, post_id: str) -> List[Dict[str, Any]]:
        """
        根据帖子ID查找图片
        
        Args:
            post_id: 帖子ID
            
        Returns:
            图片信息列表
        """
        results = []
        for filename, record in self._metadata_cache.items():
            if record.get('post_id') == post_id:
                results.append({
                    'filename': filename,
                    **record
                })
        return results
    
    def find_images_by_url(self, original_url: str) -> Optional[Dict[str, Any]]:
        """
        根据原始URL查找图片
        
        Args:
            original_url: 原始图片URL
            
        Returns:
            图片信息或None
        """
        for filename, record in self._metadata_cache.items():
            if record.get('original_url') == original_url:
                return {
                    'filename': filename,
                    **record
                }
        return None
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            total_images = len(self._metadata_cache)
            total_size = sum(record.get('file_size', 0) for record in self._metadata_cache.values())
            total_size_mb = round(total_size / (1024 * 1024), 2)
            
            # 按帖子统计
            post_counts = {}
            for record in self._metadata_cache.values():
                post_id = record.get('post_id', 'unknown')
                post_counts[post_id] = post_counts.get(post_id, 0) + 1
            
            # 文件大小分布
            size_ranges = {'<1MB': 0, '1-5MB': 0, '5-10MB': 0, '>10MB': 0}
            for record in self._metadata_cache.values():
                size_mb = record.get('file_size_mb', 0)
                if size_mb < 1:
                    size_ranges['<1MB'] += 1
                elif size_mb < 5:
                    size_ranges['1-5MB'] += 1
                elif size_mb < 10:
                    size_ranges['5-10MB'] += 1
                else:
                    size_ranges['>10MB'] += 1
            
            return {
                'total_images': total_images,
                'total_size_bytes': total_size,
                'total_size_mb': total_size_mb,
                'average_size_mb': round(total_size_mb / total_images, 3) if total_images > 0 else 0,
                'images_dir': str(self.images_dir),
                'metadata_file': str(self.metadata_file),
                'post_distribution': dict(sorted(post_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                'size_distribution': size_ranges
            }
            
        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
            return {'error': str(e)}
    
    @handle_exception
    async def cleanup_orphaned_files(self) -> int:
        """
        清理孤立的图片文件（有文件但无元数据记录）
        
        Returns:
            清理的文件数量
        """
        try:
            if not self.images_dir.exists():
                return 0
            
            registered_files = set(self._metadata_cache.keys())
            actual_files = {f.name for f in self.images_dir.iterdir() if f.is_file()}
            
            # 找到孤立文件
            orphaned_files = actual_files - registered_files
            
            deleted_count = 0
            for filename in orphaned_files:
                try:
                    file_path = self.images_dir / filename
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"删除孤立文件: {filename}")
                except Exception as e:
                    logger.warning(f"删除孤立文件失败 {filename}: {e}")
            
            if deleted_count > 0:
                logger.info(f"清理孤立文件完成: {deleted_count} 个文件")
            
            return deleted_count
            
        except Exception as e:
            raise StorageError(f"清理孤立文件失败: {str(e)}")
    
    @handle_exception
    async def cleanup_missing_records(self) -> int:
        """
        清理丢失文件的元数据记录
        
        Returns:
            清理的记录数量
        """
        try:
            if not self.images_dir.exists():
                return 0
            
            missing_records = []
            
            for filename, record in self._metadata_cache.items():
                local_path = Path(record.get('local_path', self.images_dir / filename))
                if not local_path.exists():
                    missing_records.append(filename)
            
            # 删除丢失文件的记录
            for filename in missing_records:
                del self._metadata_cache[filename]
            
            if missing_records:
                self._save_metadata()
                logger.info(f"清理丢失文件记录完成: {len(missing_records)} 个记录")
            
            return len(missing_records)
            
        except Exception as e:
            raise StorageError(f"清理丢失文件记录失败: {str(e)}")
    
    @handle_exception
    async def cleanup_old_images(self, days: int = 30) -> int:
        """
        清理旧的图片文件
        
        Args:
            days: 保留天数
            
        Returns:
            清理的文件数量
        """
        try:
            if not self.images_dir.exists():
                return 0
            
            import time
            cutoff_time = time.time() - (days * 24 * 3600)
            deleted_count = 0
            deleted_records = []
            
            for filename, record in list(self._metadata_cache.items()):
                local_path = Path(record.get('local_path', self.images_dir / filename))
                
                if local_path.exists():
                    # 检查文件修改时间
                    if local_path.stat().st_mtime < cutoff_time:
                        try:
                            local_path.unlink()
                            deleted_records.append(filename)
                            deleted_count += 1
                            logger.debug(f"删除旧图片: {filename}")
                        except Exception as e:
                            logger.warning(f"删除旧图片失败 {filename}: {e}")
            
            # 删除对应的元数据记录
            for filename in deleted_records:
                if filename in self._metadata_cache:
                    del self._metadata_cache[filename]
            
            if deleted_records:
                self._save_metadata()
                logger.info(f"清理旧图片完成: {deleted_count} 个文件")
            
            return deleted_count
            
        except Exception as e:
            raise StorageError(f"清理旧图片失败: {str(e)}")
    
    @handle_exception
    async def export_metadata(self, output_path: str) -> bool:
        """
        导出图片元数据
        
        Args:
            output_path: 输出路径
            
        Returns:
            是否导出成功
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                'export_time': datetime.now().isoformat(),
                'total_images': len(self._metadata_cache),
                'images': self._metadata_cache
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功导出图片元数据到: {output_path}")
            return True
            
        except Exception as e:
            raise StorageError(f"导出图片元数据失败: {str(e)}")
    
    @handle_exception
    async def import_metadata(self, import_path: str) -> int:
        """
        导入图片元数据
        
        Args:
            import_path: 导入文件路径
            
        Returns:
            导入的记录数量
        """
        try:
            import_path = Path(import_path)
            if not import_path.exists():
                raise StorageError(f"导入文件不存在: {import_path}")
            
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            imported_images = import_data.get('images', {})
            imported_count = 0
            
            for filename, record in imported_images.items():
                # 检查文件是否存在
                local_path = Path(record.get('local_path', self.images_dir / filename))
                if local_path.exists():
                    self._metadata_cache[filename] = record
                    imported_count += 1
                else:
                    logger.warning(f"跳过不存在的图片文件: {local_path}")
            
            if imported_count > 0:
                self._save_metadata()
                logger.info(f"成功导入图片元数据: {imported_count} 个记录")
            
            return imported_count
            
        except Exception as e:
            raise StorageError(f"导入图片元数据失败: {str(e)}")
    
    def get_duplicate_images(self) -> List[Dict[str, Any]]:
        """
        查找重复的图片（基于original_url）
        
        Returns:
            重复图片信息列表
        """
        url_groups = {}
        
        # 按URL分组
        for filename, record in self._metadata_cache.items():
            url = record.get('original_url')
            if url:
                if url not in url_groups:
                    url_groups[url] = []
                url_groups[url].append({
                    'filename': filename,
                    **record
                })
        
        # 找到重复的URL
        duplicates = []
        for url, images in url_groups.items():
            if len(images) > 1:
                duplicates.append({
                    'original_url': url,
                    'count': len(images),
                    'images': images
                })
        
        return duplicates
    
    @handle_exception
    async def remove_duplicates(self, keep_newest: bool = True) -> int:
        """
        移除重复的图片
        
        Args:
            keep_newest: 是否保留最新的文件
            
        Returns:
            移除的文件数量
        """
        try:
            duplicates = self.get_duplicate_images()
            removed_count = 0
            
            for duplicate_group in duplicates:
                images = duplicate_group['images']
                
                # 排序决定保留哪个文件
                if keep_newest:
                    images.sort(key=lambda x: x.get('registered_time', ''), reverse=True)
                else:
                    images.sort(key=lambda x: x.get('registered_time', ''))
                
                # 保留第一个，删除其余的
                for image in images[1:]:
                    try:
                        filename = image['filename']
                        local_path = Path(image['local_path'])
                        
                        # 删除文件
                        if local_path.exists():
                            local_path.unlink()
                        
                        # 删除元数据记录
                        if filename in self._metadata_cache:
                            del self._metadata_cache[filename]
                        
                        removed_count += 1
                        logger.debug(f"删除重复图片: {filename}")
                        
                    except Exception as e:
                        logger.warning(f"删除重复图片失败: {e}")
            
            if removed_count > 0:
                self._save_metadata()
                logger.info(f"删除重复图片完成: {removed_count} 个文件")
            
            return removed_count
            
        except Exception as e:
            raise StorageError(f"删除重复图片失败: {str(e)}")
