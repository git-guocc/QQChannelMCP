"""
图片下载模块
"""

import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, unquote
import hashlib
import mimetypes

from ..core.config import QQChannelConfig
from ..core.exceptions import NetworkError, handle_exception

logger = logging.getLogger(__name__)


class ImageDownloader:
    """图片下载器"""
    
    def __init__(self, config: Optional[QQChannelConfig] = None):
        self.config = config or QQChannelConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 支持的图片格式
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        
        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://pd.qq.com/',
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    @handle_exception
    async def download_images(self, image_urls: List[str], base_filename: str = None) -> List[Dict[str, str]]:
        """
        批量下载图片
        
        Args:
            image_urls: 图片URL列表
            base_filename: 基础文件名
            
        Returns:
            下载结果列表，包含原始URL和本地路径
        """
        if not image_urls:
            return []
        
        logger.info(f"开始下载 {len(image_urls)} 张图片")
        
        results = []
        
        async with self:
            # 并发下载图片
            tasks = []
            for i, url in enumerate(image_urls):
                filename = f"{base_filename}_{i}" if base_filename else None
                task = self._download_single_image(url, filename)
                tasks.append(task)
            
            # 等待所有下载完成
            download_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for i, result in enumerate(download_results):
                if isinstance(result, Exception):
                    logger.error(f"下载图片失败 {image_urls[i]}: {result}")
                    results.append({
                        'url': image_urls[i],
                        'local_path': None,
                        'success': False,
                        'error': str(result)
                    })
                else:
                    results.append(result)
        
        success_count = sum(1 for r in results if r['success'])
        logger.info(f"图片下载完成: 成功 {success_count}/{len(image_urls)}")
        
        return results
    
    async def _download_single_image(self, image_url: str, filename: str = None) -> Dict[str, str]:
        """
        下载单张图片
        
        Args:
            image_url: 图片URL
            filename: 自定义文件名
            
        Returns:
            下载结果
        """
        try:
            if not self.session:
                raise NetworkError("HTTP会话未初始化")
            
            # 验证URL
            if not self._is_valid_image_url(image_url):
                raise NetworkError(f"无效的图片URL: {image_url}")
            
            # 生成本地文件路径
            local_path = self._generate_local_path(image_url, filename)
            
            # 如果文件已存在，直接返回
            if local_path.exists():
                logger.debug(f"图片已存在，跳过下载: {local_path}")
                return {
                    'url': image_url,
                    'local_path': str(local_path),
                    'success': True,
                    'cached': True
                }
            
            # 下载图片
            async with self.session.get(image_url) as response:
                if response.status != 200:
                    raise NetworkError(f"HTTP错误 {response.status}: {image_url}")
                
                # 检查内容类型
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    logger.warning(f"可能不是图片文件: {content_type}")
                
                # 检查文件大小
                content_length = response.headers.get('content-length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > 10:  # 限制10MB
                        raise NetworkError(f"图片文件过大: {size_mb:.1f}MB")
                
                # 确保目录存在
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 保存文件
                with open(local_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                
                logger.debug(f"图片下载成功: {local_path}")
                
                return {
                    'url': image_url,
                    'local_path': str(local_path),
                    'success': True,
                    'size': local_path.stat().st_size,
                    'content_type': content_type
                }
                
        except Exception as e:
            logger.error(f"下载图片失败 {image_url}: {e}")
            return {
                'url': image_url,
                'local_path': None,
                'success': False,
                'error': str(e)
            }
    
    def _is_valid_image_url(self, url: str) -> bool:
        """检查是否为有效的图片URL"""
        if not url:
            return False
        
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # 检查是否为HTTPS/HTTP
            if parsed.scheme not in ['http', 'https']:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _generate_local_path(self, image_url: str, filename: str = None) -> Path:
        """生成本地文件路径"""
        try:
            parsed_url = urlparse(image_url)
            
            if filename:
                # 使用自定义文件名
                base_name = filename
            else:
                # 从URL生成文件名
                url_path = unquote(parsed_url.path)
                if '/' in url_path:
                    base_name = url_path.split('/')[-1]
                else:
                    # 使用URL哈希作为文件名
                    url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
                    base_name = f"img_{url_hash}"
            
            # 移除文件名中的非法字符
            base_name = self._sanitize_filename(base_name)
            
            # 确定文件扩展名
            extension = self._get_file_extension(image_url, parsed_url.path)
            
            # 如果没有扩展名，添加默认扩展名
            if not extension:
                extension = '.jpg'
            
            # 确保扩展名正确
            if not base_name.endswith(extension):
                if '.' in base_name:
                    base_name = base_name.rsplit('.', 1)[0]
                base_name += extension
            
            # 构建完整路径
            images_dir = Path(self.config.images_dir)
            return images_dir / base_name
            
        except Exception as e:
            logger.error(f"生成本地路径失败: {e}")
            # 使用URL哈希作为后备方案
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
            images_dir = Path(self.config.images_dir)
            return images_dir / f"img_{url_hash}.jpg"
    
    def _get_file_extension(self, url: str, path: str) -> str:
        """获取文件扩展名"""
        # 先从路径中获取
        if '.' in path:
            ext = '.' + path.split('.')[-1].lower()
            if ext in self.supported_formats:
                return ext
        
        # 从URL参数中获取
        if 'format=' in url:
            format_match = url.split('format=')[1].split('&')[0]
            if format_match in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                return f'.{format_match}'
        
        # 根据域名判断
        if 'qpic.cn' in url or 'gtimg.cn' in url:
            return '.jpg'  # QQ图片通常是jpg格式
        
        return ''
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # 移除或替换非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename.strip()
    
    async def get_image_info(self, image_url: str) -> Optional[Dict[str, Any]]:
        """
        获取图片信息（不下载）
        
        Args:
            image_url: 图片URL
            
        Returns:
            图片信息字典
        """
        try:
            if not self.session:
                async with self:
                    return await self._get_image_info_internal(image_url)
            else:
                return await self._get_image_info_internal(image_url)
                
        except Exception as e:
            logger.error(f"获取图片信息失败 {image_url}: {e}")
            return None
    
    async def _get_image_info_internal(self, image_url: str) -> Dict[str, Any]:
        """内部获取图片信息方法"""
        async with self.session.head(image_url) as response:
            if response.status != 200:
                raise NetworkError(f"HTTP错误 {response.status}")
            
            headers = response.headers
            
            return {
                'url': image_url,
                'content_type': headers.get('content-type', ''),
                'content_length': int(headers.get('content-length', 0)),
                'last_modified': headers.get('last-modified', ''),
                'server': headers.get('server', ''),
                'size_mb': int(headers.get('content-length', 0)) / (1024 * 1024)
            }
    
    def cleanup_old_images(self, days: int = 30) -> int:
        """
        清理旧的图片文件
        
        Args:
            days: 保留天数
            
        Returns:
            删除的文件数量
        """
        try:
            images_dir = Path(self.config.images_dir)
            if not images_dir.exists():
                return 0
            
            import time
            cutoff_time = time.time() - (days * 24 * 3600)
            deleted_count = 0
            
            for image_file in images_dir.iterdir():
                if image_file.is_file() and image_file.stat().st_mtime < cutoff_time:
                    try:
                        image_file.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"删除文件失败 {image_file}: {e}")
            
            logger.info(f"清理完成，删除了 {deleted_count} 个旧图片文件")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理图片失败: {e}")
            return 0
