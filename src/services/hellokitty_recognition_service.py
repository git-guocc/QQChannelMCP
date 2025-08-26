#!/usr/bin/env python3
"""
HelloKitty图片识别服务
完全独立的图片识别功能，与下载功能解耦
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from core.ai_client import AIClientManager, AIProvider
from core.settings import settings
from utils.image_processor import ImageProcessor

logger = logging.getLogger(__name__)

@dataclass
class RecognitionResult:
    """图片识别结果"""
    image_path: str
    is_hellokitty: bool
    confidence: float
    ai_response: str
    provider: str
    processing_time: float
    file_size: int
    original_format: str

class HelloKittyRecognitionService:
    """HelloKitty图片识别服务"""
    
    def __init__(self, preferred_provider: AIProvider = AIProvider.OPENROUTER):
        """
        初始化识别服务
        
        Args:
            preferred_provider: 优先使用的AI提供商
        """
        self.preferred_provider = preferred_provider
        self.config = settings
        self.ai_manager = AIClientManager(self.config, preferred_provider)
        
        # 识别统计
        self.stats = {
            "total_processed": 0,
            "hellokitty_found": 0,
            "processing_failed": 0,
            "total_processing_time": 0.0
        }
    
    async def recognize_single_image(self, image_path: str) -> Optional[RecognitionResult]:
        """
        识别单张图片
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            RecognitionResult: 识别结果，失败时返回None
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 验证文件
            if not self._validate_image_file(image_path):
                return None
            
            # 获取AI客户端
            ai_client = await self.ai_manager.get_available_client()
            if not ai_client:
                logger.error("无法获取AI客户端")
                return None
            
            # 构建识别提示词
            prompt = self._build_recognition_prompt()
            
            # 调用AI分析
            result = await ai_client.analyze_image(image_path, prompt)
            
            if result.success:
                # 解析结果
                is_hellokitty = self._parse_ai_response(result.content)
                
                # 获取图片信息
                img_info = ImageProcessor.get_image_info(image_path)
                
                # 创建识别结果
                recognition_result = RecognitionResult(
                    image_path=image_path,
                    is_hellokitty=is_hellokitty,
                    confidence=result.confidence,
                    ai_response=result.content.strip(),
                    provider=result.metadata.get("provider", "unknown"),
                    processing_time=asyncio.get_event_loop().time() - start_time,
                    file_size=img_info.get("file_size", 0),
                    original_format=img_info.get("format", "unknown")
                )
                
                # 更新统计
                self._update_stats(recognition_result)
                
                logger.info(f"图片识别成功: {image_path}")
                logger.info(f"  HelloKitty: {'是' if is_hellokitty else '否'}")
                logger.info(f"  置信度: {result.confidence}")
                logger.info(f"  提供商: {recognition_result.provider}")
                logger.info(f"  处理时间: {recognition_result.processing_time:.2f}秒")
                
                return recognition_result
            else:
                logger.error(f"AI分析失败: {image_path}")
                logger.error(f"  错误: {result.error}")
                self.stats["processing_failed"] += 1
                return None
                
        except Exception as e:
            logger.error(f"图片识别异常: {image_path}")
            logger.error(f"  异常: {e}")
            self.stats["processing_failed"] += 1
            return None
    
    async def recognize_multiple_images(self, image_paths: List[str]) -> List[RecognitionResult]:
        """
        批量识别多张图片
        
        Args:
            image_paths: 图片文件路径列表
            
        Returns:
            List[RecognitionResult]: 识别结果列表
        """
        logger.info(f"开始批量识别 {len(image_paths)} 张图片...")
        
        # 并发处理图片
        tasks = [self.recognize_single_image(img_path) for img_path in image_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤有效结果
        valid_results = []
        for result in results:
            if isinstance(result, RecognitionResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"批量识别异常: {result}")
                self.stats["processing_failed"] += 1
        
        logger.info(f"批量识别完成: {len(valid_results)}/{len(image_paths)} 成功")
        return valid_results
    
    async def recognize_directory(self, directory_path: str, pattern: str = "*_image_*.jpg") -> List[RecognitionResult]:
        """
        识别目录中的所有图片
        
        Args:
            directory_path: 目录路径
            pattern: 文件匹配模式
            
        Returns:
            List[RecognitionResult]: 识别结果列表
        """
        directory = Path(directory_path)
        if not directory.exists():
            logger.error(f"目录不存在: {directory_path}")
            return []
        
        # 查找图片文件
        image_files = list(directory.glob(pattern))
        if not image_files:
            logger.info(f"目录中没有找到匹配的图片: {pattern}")
            return []
        
        logger.info(f"在目录 {directory_path} 中找到 {len(image_files)} 张图片")
        
        # 批量识别
        image_paths = [str(img_file) for img_file in image_files]
        return await self.recognize_multiple_images(image_paths)
    
    def _validate_image_file(self, image_path: str) -> bool:
        """验证图片文件"""
        try:
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return False
            
            if not os.path.isfile(image_path):
                logger.error(f"路径不是文件: {image_path}")
                return False
            
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                logger.error(f"图片文件为空: {image_path}")
                return False
            
            # 验证图片格式
            if not ImageProcessor.validate_image(image_path):
                logger.error(f"图片文件无效: {image_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"文件验证失败: {image_path}, 错误: {e}")
            return False
    
    def _build_recognition_prompt(self) -> str:
        """构建识别提示词"""
        return """
        请分析这张图片是否包含HelloKitty元素。
        
        HelloKitty特征：
        - 白色小猫形象，通常戴着蝴蝶结
        - 可爱的卡通风格，大眼睛，无嘴巴
        - HelloKitty品牌相关商品或图案
        - 粉色、红色、蓝色等HelloKitty常见颜色
        - 可能出现在服装、饰品、玩具、文具等物品上
        
        请只回答：是 或 否
        """
    
    def _parse_ai_response(self, content: str) -> bool:
        """解析AI响应"""
        content_lower = content.strip().lower()
        return any(keyword in content_lower for keyword in ["是", "yes", "true", "包含", "有"])
    
    def _update_stats(self, result: RecognitionResult):
        """更新统计信息"""
        self.stats["total_processed"] += 1
        if result.is_hellokitty:
            self.stats["hellokitty_found"] += 1
        self.stats["total_processing_time"] += result.processing_time
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self.stats["total_processed"]
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            "success_rate": (total - self.stats["processing_failed"]) / total * 100,
            "hellokitty_rate": self.stats["hellokitty_found"] / total * 100,
            "avg_processing_time": self.stats["total_processing_time"] / total
        }
    
    def print_statistics(self):
        """打印统计信息"""
        stats = self.get_statistics()
        
        print("\n" + "="*50)
        print("🎀 HelloKitty图片识别统计报告")
        print("="*50)
        print(f"📸 总处理图片: {stats['total_processed']}")
        print(f"🎀 HelloKitty图片: {stats['hellokitty_found']}")
        print(f"❌ 处理失败: {stats['processing_failed']}")
        print(f"⏱️  总处理时间: {stats['total_processing_time']:.2f}秒")
        
        if stats['total_processed'] > 0:
            print(f"🎉 成功率: {stats['success_rate']:.1f}%")
            print(f"🎀 HelloKitty识别率: {stats['hellokitty_rate']:.1f}%")
            print(f"⚡ 平均处理时间: {stats['avg_processing_time']:.2f}秒")
        
        print("="*50)
