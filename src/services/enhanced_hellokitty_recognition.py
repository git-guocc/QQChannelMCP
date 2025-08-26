#!/usr/bin/env python3
"""
增强的HelloKitty识别服务
使用多种策略来提高识别准确率，减少漏识别
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json

from core.ai_client import AIClientManager, AIProvider
from core.settings import settings
from utils.image_processor import ImageProcessor

logger = logging.getLogger(__name__)

@dataclass
class RecognitionResult:
    """增强的识别结果"""
    image_path: str
    is_hellokitty: bool
    confidence: float
    recognition_method: str
    ai_response: str = ""
    provider: str = ""
    processing_time: float = 0.0
    file_size: int = 0
    original_format: str = ""
    features: Dict[str, Any] = None
    needs_manual_review: bool = False

class EnhancedHelloKittyRecognitionService:
    """增强的HelloKitty识别服务"""
    
    def __init__(self, preferred_provider: AIProvider = AIProvider.OPENROUTER):
        self.preferred_provider = preferred_provider
        self.config = settings
        self.ai_manager = AIClientManager(self.config, preferred_provider)
        
        # 识别统计
        self.stats = {
            "total_processed": 0,
            "hellokitty_found": 0,
            "processing_failed": 0,
            "ai_recognition_success": 0,
            "feature_based_recognition": 0,
            "keyword_based_recognition": 0,
            "conservative_recognition": 0,
            "total_processing_time": 0.0
        }
        
        # 已知的HelloKitty特征
        self.hellokitty_features = {
            "colors": {
                "pink": [(255, 192, 203), (255, 182, 193), (255, 20, 147), (255, 105, 180)],
                "white": [(255, 255, 255), (250, 250, 250), (245, 245, 245)],
                "red": [(255, 0, 0), (220, 20, 60), (178, 34, 34)],
                "blue": [(0, 0, 255), (30, 144, 255), (100, 149, 237)]
            },
            "keywords": [
                'hellokitty', 'hello_kitty', 'hello-kitty', 'kitty', 'hello',
                'sanrio', 'kawaii', 'cute', 'cat', 'pink', 'bow', 'ribbon',
                'white', 'ears', 'whiskers', 'nose', 'eyes', 'flower', 'star',
                'heart', 'angel', 'princess', 'fairy', 'magic', 'dream'
            ],
            "size_ranges": [(100, 5000), (100, 5000)]  # (min_width, max_width), (min_height, max_height)
        }
    
    async def recognize_single_image(self, image_path: str) -> Optional[RecognitionResult]:
        """识别单张图片"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 验证文件
            if not self._validate_image_file(image_path):
                return None
            
            # 获取文件信息
            file_size = os.path.getsize(image_path)
            original_format = self._get_image_format(image_path)
            
            logger.info(f"开始识别图片: {image_path}")
            
            # 策略1: AI识别（最高优先级）
            ai_result = await self._ai_recognition(image_path)
            if ai_result and ai_result.is_hellokitty:
                result = RecognitionResult(
                    image_path=image_path,
                    is_hellokitty=True,
                    confidence=ai_result.confidence,
                    recognition_method="AI识别",
                    ai_response=ai_result.content,
                    provider=ai_result.metadata.get('provider', 'unknown'),
                    processing_time=asyncio.get_event_loop().time() - start_time,
                    file_size=file_size,
                    original_format=original_format
                )
                self._update_stats(result)
                return result
            
            # 策略2: 特征识别
            feature_result = await self._feature_based_recognition(image_path)
            if feature_result:
                result = RecognitionResult(
                    image_path=image_path,
                    is_hellokitty=True,
                    confidence=0.8,
                    recognition_method="特征识别",
                    processing_time=asyncio.get_event_loop().time() - start_time,
                    file_size=file_size,
                    original_format=original_format,
                    features=feature_result
                )
                self._update_stats(result)
                return result
            
            # 策略3: 关键词识别
            keyword_result = self._keyword_based_recognition(image_path)
            if keyword_result:
                result = RecognitionResult(
                    image_path=image_path,
                    is_hellokitty=True,
                    confidence=0.7,
                    recognition_method="关键词识别",
                    processing_time=asyncio.get_event_loop().time() - start_time,
                    file_size=file_size,
                    original_format=original_format
                )
                self._update_stats(result)
                return result
            
            # 策略4: 保守策略（对于HelloKitty频道）
            conservative_result = self._conservative_recognition(image_path)
            if conservative_result:
                result = RecognitionResult(
                    image_path=image_path,
                    is_hellokitty=True,
                    confidence=0.6,
                    recognition_method="保守策略",
                    processing_time=asyncio.get_event_loop().time() - start_time,
                    file_size=file_size,
                    original_format=original_format,
                    needs_manual_review=True
                )
                self._update_stats(result)
                return result
            
            # 如果所有策略都失败，标记为非HelloKitty
            result = RecognitionResult(
                image_path=image_path,
                is_hellokitty=False,
                confidence=0.3,
                recognition_method="未识别",
                processing_time=asyncio.get_event_loop().time() - start_time,
                file_size=file_size,
                original_format=original_format
            )
            self._update_stats(result)
            return result
            
        except Exception as e:
            logger.error(f"图片识别失败: {image_path}, 错误: {e}")
            self.stats["processing_failed"] += 1
            return None
    
    async def _ai_recognition(self, image_path: str) -> Optional[RecognitionResult]:
        """AI识别策略"""
        try:
            # 构建优化的提示词
            prompt = """
            请仔细分析这张图片是否包含HelloKitty元素。
            
            HelloKitty特征包括但不限于：
            - 白色小猫形象，通常戴着蝴蝶结
            - 可爱的卡通风格，大眼睛，无嘴巴
            - HelloKitty品牌相关商品或图案
            - 粉色、红色、蓝色等HelloKitty常见颜色
            - 可能出现在服装、饰品、玩具、文具等物品上
            - 各种HelloKitty变体、周边产品
            
            请仔细分析后回答：是 或 否
            """
            
            # 获取AI客户端
            client = await self.ai_manager.get_available_client()
            if not client:
                return None
            
            # 调用AI分析
            result = await client.analyze_image(image_path, prompt)
            
            if result.success:
                content = result.content.strip().lower()
                is_hellokitty = "是" in content or "yes" in content or "true" in content
                
                if is_hellokitty:
                    self.stats["ai_recognition_success"] += 1
                    logger.info(f"AI识别成功: {image_path}")
                
                return RecognitionResult(
                    image_path=image_path,
                    is_hellokitty=is_hellokitty,
                    confidence=result.confidence,
                    recognition_method="AI识别",
                    ai_response=result.content,
                    provider=result.metadata.get('provider', 'unknown')
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"AI识别失败: {image_path}, 错误: {e}")
            return None
    
    async def _feature_based_recognition(self, image_path: str) -> Optional[Dict[str, Any]]:
        """基于图片特征的识别"""
        try:
            from PIL import Image
            import numpy as np
            
            with Image.open(image_path) as img:
                # 转换为RGB模式
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 获取图片尺寸
                width, height = img.size
                
                # 检查尺寸范围
                if not (self.hellokitty_features["size_ranges"][0][0] <= width <= self.hellokitty_features["size_ranges"][0][1] and
                       self.hellokitty_features["size_ranges"][1][0] <= height <= self.hellokitty_features["size_ranges"][1][1]):
                    return None
                
                # 转换为numpy数组进行颜色分析
                img_array = np.array(img)
                colors = img_array.reshape(-1, 3)
                
                # 计算颜色分布
                color_features = {}
                for color_name, color_values in self.hellokitty_features["colors"].items():
                    color_count = 0
                    for target_color in color_values:
                        # 使用颜色距离来判断相似性
                        color_distances = np.sqrt(np.sum((colors - target_color) ** 2, axis=1))
                        color_count += np.sum(color_distances < 50)  # 颜色距离阈值
                    
                    color_features[color_name] = color_count
                
                # 检查是否包含足够的HelloKitty特征颜色
                total_pixels = width * height
                color_threshold = total_pixels * 0.01  # 1%的像素阈值
                
                has_hellokitty_colors = any(count > color_threshold for count in color_features.values())
                
                if has_hellokitty_colors:
                    self.stats["feature_based_recognition"] += 1
                    logger.info(f"特征识别成功: {image_path}, 颜色特征: {color_features}")
                    return {
                        "colors": color_features,
                        "dimensions": (width, height),
                        "total_pixels": total_pixels
                    }
                
                return None
                
        except Exception as e:
            logger.warning(f"特征识别失败: {image_path}, 错误: {e}")
            return None
    
    def _keyword_based_recognition(self, image_path: str) -> bool:
        """基于关键词的识别"""
        try:
            filename = os.path.basename(image_path).lower()
            path_parts = image_path.lower().split('/')
            
            # 检查文件名和路径中的关键词
            for keyword in self.hellokitty_features["keywords"]:
                if keyword in filename:
                    logger.info(f"关键词识别成功: {filename} (关键词: {keyword})")
                    self.stats["keyword_based_recognition"] += 1
                    return True
                
                for part in path_parts:
                    if keyword in part:
                        logger.info(f"关键词识别成功: {part} (关键词: {keyword})")
                        self.stats["keyword_based_recognition"] += 1
                        return True
            
            return False
            
        except Exception as e:
            logger.warning(f"关键词识别失败: {image_path}, 错误: {e}")
            return False
    
    def _conservative_recognition(self, image_path: str) -> bool:
        """保守策略识别"""
        try:
            # 对于HelloKitty频道，使用保守策略
            # 检查是否在HelloKitty相关目录中
            path_parts = image_path.lower().split('/')
            
            # 如果路径包含HelloKitty相关关键词，使用保守策略
            hellokitty_indicators = ['hellokitty', 'hello', 'kitty', 'sanrio', 'kawaii']
            
            for indicator in hellokitty_indicators:
                for part in path_parts:
                    if indicator in part:
                        logger.info(f"保守策略识别: {image_path} (指示词: {indicator})")
                        self.stats["conservative_recognition"] += 1
                        return True
            
            return False
            
        except Exception as e:
            logger.warning(f"保守策略识别失败: {image_path}, 错误: {e}")
            return False
    
    def _validate_image_file(self, image_path: str) -> bool:
        """验证图片文件"""
        try:
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return False
            
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                logger.error(f"图片文件为空: {image_path}")
                return False
            
            # 检查文件扩展名
            valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.avif', '.bmp'}
            file_ext = os.path.splitext(image_path)[1].lower()
            
            if file_ext not in valid_extensions:
                logger.warning(f"不支持的图片格式: {image_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"文件验证失败: {image_path}, 错误: {e}")
            return False
    
    def _get_image_format(self, image_path: str) -> str:
        """获取图片格式"""
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                return img.format.lower() if img.format else 'unknown'
        except Exception:
            return os.path.splitext(image_path)[1].lower().lstrip('.')
    
    def _update_stats(self, result: RecognitionResult):
        """更新统计信息"""
        self.stats["total_processed"] += 1
        if result.is_hellokitty:
            self.stats["hellokitty_found"] += 1
        self.stats["total_processing_time"] += result.processing_time
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        if stats["total_processed"] > 0:
            stats["success_rate"] = (stats["hellokitty_found"] / stats["total_processed"]) * 100
            stats["avg_processing_time"] = stats["total_processing_time"] / stats["total_processed"]
        return stats
    
    def print_statistics(self):
        """打印统计信息"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("🎀 HelloKitty识别统计报告")
        print("="*60)
        print(f"📊 总处理图片数: {stats['total_processed']}")
        print(f"🎯 HelloKitty识别数: {stats['hellokitty_found']}")
        print(f"❌ 处理失败数: {stats['processing_failed']}")
        
        if 'success_rate' in stats:
            print(f"🎉 识别成功率: {stats['success_rate']:.1f}%")
        
        print(f"\n🔍 识别方法统计:")
        print(f"  🤖 AI识别成功: {stats['ai_recognition_success']}")
        print(f"  🎨 特征识别: {stats['feature_based_recognition']}")
        print(f"  🔑 关键词识别: {stats['keyword_based_recognition']}")
        print(f"  🛡️ 保守策略: {stats['conservative_recognition']}")
        
        if 'avg_processing_time' in stats:
            print(f"\n⏱️ 平均处理时间: {stats['avg_processing_time']:.3f} 秒")
        
        print("="*60)
