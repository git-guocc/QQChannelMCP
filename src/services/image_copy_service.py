#!/usr/bin/env python3
"""
图片复制服务
负责将识别出的HelloKitty图片复制到指定目录
"""

import os
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CopyResult:
    """复制结果"""
    source_path: str
    destination_path: str
    success: bool
    file_size: int
    copy_time: float
    error_message: str = ""

class ImageCopyService:
    """图片复制服务"""
    
    def __init__(self, source_directory: str, destination_directory: str = None):
        """
        初始化复制服务
        
        Args:
            source_directory: 源图片目录
            destination_directory: 目标目录（默认为HelloKitty文件夹）
        """
        self.source_directory = Path(source_directory)
        self.destination_directory = Path(destination_directory) if destination_directory else self.source_directory.parent / "HelloKitty"
        
        # 确保目标目录存在
        self.destination_directory.mkdir(exist_ok=True)
        
        # 复制统计
        self.stats = {
            "total_copied": 0,
            "copy_failed": 0,
            "total_copy_size": 0,
            "total_copy_time": 0.0
        }
    
    def copy_hellokitty_images(self, recognition_results: List[Any]) -> List[CopyResult]:
        """
        复制HelloKitty图片到目标目录
        
        Args:
            recognition_results: 识别结果列表（包含is_hellokitty字段）
            
        Returns:
            List[CopyResult]: 复制结果列表
        """
        logger.info(f"开始复制HelloKitty图片到: {self.destination_directory}")
        
        copy_results = []
        hellokitty_images = [r for r in recognition_results if r.is_hellokitty]
        
        if not hellokitty_images:
            logger.info("没有找到HelloKitty图片需要复制")
            return []
        
        logger.info(f"找到 {len(hellokitty_images)} 张HelloKitty图片需要复制")
        
        for result in hellokitty_images:
            copy_result = self._copy_single_image(result.image_path)
            copy_results.append(copy_result)
            
            if copy_result.success:
                self.stats["total_copied"] += 1
                self.stats["total_copy_size"] += copy_result.file_size
                self.stats["total_copy_time"] += copy_result.copy_time
            else:
                self.stats["copy_failed"] += 1
        
        logger.info(f"复制完成: {self.stats['total_copied']}/{len(hellokitty_images)} 成功")
        return copy_results
    
    def _copy_single_image(self, source_path: str) -> CopyResult:
        """复制单张图片"""
        import time
        
        start_time = time.time()
        source_file = Path(source_path)
        
        try:
            # 检查源文件
            if not source_file.exists():
                return CopyResult(
                    source_path=source_path,
                    destination_path="",
                    success=False,
                    file_size=0,
                    copy_time=0,
                    error_message="源文件不存在"
                )
            
            # 构建目标路径
            dest_file = self.destination_directory / source_file.name
            
            # 检查目标文件是否已存在
            if dest_file.exists():
                logger.warning(f"目标文件已存在，将被覆盖: {dest_file}")
            
            # 执行复制
            shutil.copy2(source_file, dest_file)
            
            # 验证复制结果
            if dest_file.exists():
                copy_time = time.time() - start_time
                file_size = dest_file.stat().st_size
                
                logger.info(f"图片复制成功: {source_file.name} -> {dest_file}")
                
                return CopyResult(
                    source_path=source_path,
                    destination_path=str(dest_file),
                    success=True,
                    file_size=file_size,
                    copy_time=copy_time
                )
            else:
                return CopyResult(
                    source_path=source_path,
                    destination_path=str(dest_file),
                    success=False,
                    file_size=0,
                    copy_time=time.time() - start_time,
                    error_message="复制后目标文件不存在"
                )
                
        except Exception as e:
            copy_time = time.time() - start_time
            logger.error(f"图片复制失败: {source_path}, 错误: {e}")
            
            return CopyResult(
                source_path=source_path,
                destination_path="",
                success=False,
                file_size=0,
                copy_time=copy_time,
                error_message=str(e)
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取复制统计信息"""
        total = self.stats["total_copied"] + self.stats["copy_failed"]
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            "success_rate": self.stats["total_copied"] / total * 100,
            "avg_copy_time": self.stats["total_copy_time"] / self.stats["total_copied"] if self.stats["total_copied"] > 0 else 0
        }
    
    def print_statistics(self):
        """打印复制统计信息"""
        stats = self.get_statistics()
        
        print("\n" + "="*50)
        print("📁 图片复制统计报告")
        print("="*50)
        print(f"✅ 成功复制: {stats['total_copied']}")
        print(f"❌ 复制失败: {stats['copy_failed']}")
        print(f"📊 总复制大小: {stats['total_copy_size'] / 1024:.1f} KB")
        print(f"⏱️  总复制时间: {stats['total_copy_time']:.2f}秒")
        
        if stats['total_copied'] > 0:
            print(f"🎉 成功率: {stats['success_rate']:.1f}%")
            print(f"⚡ 平均复制时间: {stats['avg_copy_time']:.2f}秒")
        
        print(f"📁 目标目录: {self.destination_directory}")
        print("="*50)
