#!/usr/bin/env python3
"""
图片格式处理工具类
提供统一的图片格式检测、转换和优化功能
"""

import os
import logging
from typing import Tuple, Optional, Dict, Any
from PIL import Image
import io

logger = logging.getLogger(__name__)

class ImageProcessor:
    """图片格式处理工具类"""
    
    # 支持的图片格式
    SUPPORTED_FORMATS = {'jpeg', 'jpg', 'png', 'webp', 'bmp', 'tiff'}
    
    # 需要转换的格式（通常不被AI API支持）
    CONVERT_FORMATS = {'avif', 'webp', 'tiff', 'bmp'}
    
    # 推荐的输出格式
    RECOMMENDED_FORMAT = 'jpeg'
    
    @classmethod
    def process_image_for_ai(cls, image_path: str, target_format: str = 'jpeg', quality: int = 95) -> Tuple[bytes, str]:
        """
        处理图片格式，使其适合AI分析
        
        Args:
            image_path: 图片文件路径
            target_format: 目标格式
            quality: JPEG质量（1-100）
            
        Returns:
            Tuple[bytes, str]: (图片字节数据, MIME类型)
            
        Raises:
            FileNotFoundError: 图片文件不存在
            ValueError: 不支持的图片格式
            OSError: 图片处理失败
        """
        # 验证文件存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 检查文件大小
        file_size = os.path.getsize(image_path)
        if file_size == 0:
            raise ValueError(f"图片文件为空: {image_path}")
        
        logger.info(f"开始处理图片: {image_path} (大小: {file_size} bytes)")
        
        try:
            # 检测图片格式
            actual_format, img_mode = cls._detect_image_format(image_path)
            logger.info(f"检测到图片格式: {actual_format}, 模式: {img_mode}")
            
            # 判断是否需要转换
            if cls._needs_conversion(actual_format, target_format):
                logger.info(f"格式 {actual_format} 需要转换为 {target_format}")
                img_data, mime_type = cls._convert_image(image_path, target_format, quality)
            else:
                logger.info(f"使用原始格式: {actual_format}")
                img_data, mime_type = cls._read_original_image(image_path, actual_format)
            
            logger.info(f"图片处理完成: {len(img_data)} bytes, MIME: {mime_type}")
            return img_data, mime_type
            
        except Exception as e:
            logger.error(f"图片处理失败: {image_path}, 错误: {e}")
            raise OSError(f"图片处理失败: {e}")
    
    @classmethod
    def _detect_image_format(cls, image_path: str) -> Tuple[str, str]:
        """检测图片的实际格式和模式"""
        try:
            with Image.open(image_path) as img:
                format_name = img.format.lower() if img.format else 'unknown'
                mode = img.mode
                return format_name, mode
        except Exception as e:
            logger.warning(f"图片格式检测失败: {image_path}, 错误: {e}")
            # 使用文件扩展名作为备选
            ext = os.path.splitext(image_path)[1].lower().lstrip('.')
            return ext, 'unknown'
    
    @classmethod
    def _needs_conversion(cls, source_format: str, target_format: str) -> bool:
        """判断是否需要格式转换"""
        # 如果源格式在需要转换的列表中，或者与目标格式不同
        return (source_format in cls.CONVERT_FORMATS or 
                source_format != target_format or
                source_format not in cls.SUPPORTED_FORMATS)
    
    @classmethod
    def _convert_image(cls, image_path: str, target_format: str, quality: int) -> Tuple[bytes, str]:
        """转换图片格式"""
        try:
            with Image.open(image_path) as img:
                # 转换为RGB模式（确保兼容性）
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    logger.debug(f"图片模式从 {img.mode} 转换为 RGB")
                
                # 保存到内存缓冲区
                img_buffer = io.BytesIO()
                
                if target_format.lower() == 'jpeg':
                    img.save(img_buffer, format='JPEG', quality=quality, optimize=True)
                elif target_format.lower() == 'png':
                    img.save(img_buffer, format='PNG', optimize=True)
                else:
                    img.save(img_buffer, format=target_format.upper())
                
                img_data = img_buffer.getvalue()
                mime_type = f"image/{target_format.lower()}"
                
                logger.info(f"格式转换成功: {len(img_data)} bytes")
                return img_data, mime_type
                
        except Exception as e:
            logger.error(f"图片格式转换失败: {e}")
            raise OSError(f"图片格式转换失败: {e}")
    
    @classmethod
    def _read_original_image(cls, image_path: str, format_name: str) -> Tuple[bytes, str]:
        """读取原始图片数据"""
        try:
            with open(image_path, 'rb') as f:
                img_data = f.read()
            
            mime_type = f"image/{format_name}"
            return img_data, mime_type
            
        except Exception as e:
            logger.error(f"读取原始图片失败: {e}")
            raise OSError(f"读取原始图片失败: {e}")
    
    @classmethod
    def get_image_info(cls, image_path: str) -> Dict[str, Any]:
        """获取图片详细信息"""
        try:
            with Image.open(image_path) as img:
                info = {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'file_size': os.path.getsize(image_path),
                    'dpi': img.info.get('dpi', (None, None)),
                    'compression': img.info.get('compression', None)
                }
                return info
        except Exception as e:
            logger.error(f"获取图片信息失败: {e}")
            return {}
    
    @classmethod
    def validate_image(cls, image_path: str) -> bool:
        """验证图片文件是否有效"""
        try:
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception:
            return False
    
    @classmethod
    def optimize_for_ai(cls, image_path: str, max_size: int = 1024 * 1024) -> Tuple[bytes, str]:
        """
        为AI分析优化图片
        
        Args:
            image_path: 图片路径
            max_size: 最大文件大小（字节）
            
        Returns:
            Tuple[bytes, str]: (优化后的图片数据, MIME类型)
        """
        try:
            # 获取原始图片信息
            img_info = cls.get_image_info(image_path)
            original_size = img_info.get('file_size', 0)
            
            # 如果图片太大，进行压缩
            if original_size > max_size:
                logger.info(f"图片过大 ({original_size} bytes)，进行压缩优化")
                return cls.process_image_for_ai(image_path, 'jpeg', quality=85)
            else:
                logger.info(f"图片大小合适 ({original_size} bytes)，使用原始格式")
                return cls.process_image_for_ai(image_path)
                
        except Exception as e:
            logger.error(f"图片优化失败: {e}")
            # 降级到基本处理
            return cls.process_image_for_ai(image_path, 'jpeg', quality=80)
