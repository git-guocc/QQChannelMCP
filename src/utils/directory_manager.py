#!/usr/bin/env python3
"""
目录管理器 - 统一处理新的目录命名规范
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from core.settings import settings

class DirectoryManager:
    """目录管理器，统一处理新的目录命名规范"""
    
    def __init__(self, base_dir: str = "data/dayupdate"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_today_directory(self, posts_count: int = None) -> Path:
        """
        获取今天的目录路径
        
        Args:
            posts_count: 帖子数量，如果为None则自动查找
            
        Returns:
            今天的目录路径
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        
        # 目录命名规范：data/dayupdate/YYYY-MM-DD/
        today_dir = self.base_dir / date_str
        
        # 创建目录结构
        today_dir.mkdir(exist_ok=True)
        (today_dir / "images").mkdir(exist_ok=True)
        if settings.app.enable_video:
            (today_dir / "videos").mkdir(exist_ok=True)
        (today_dir / "gifs").mkdir(exist_ok=True)
        (today_dir / "unknown").mkdir(exist_ok=True)
        
        return today_dir
    
    def get_media_subdirectory(self, media_type: str, posts_count: int = None) -> Path:
        """
        获取指定媒体类型的子目录
        
        Args:
            media_type: 媒体类型 (images, videos, gifs, unknown)
            posts_count: 帖子数量
            
        Returns:
            媒体子目录路径
        """
        today_dir = self.get_today_directory(posts_count)
        media_dir = today_dir / media_type
        media_dir.mkdir(exist_ok=True)
        return media_dir
    
    def find_latest_directory(self) -> Optional[Path]:
        """查找最新的目录"""
        if not self.base_dir.exists():
            return None
        
        dirs = [d for d in self.base_dir.iterdir() if d.is_dir()]
        if not dirs:
            return None
        
        # 按修改时间排序，返回最新的
        return max(dirs, key=lambda x: x.stat().st_mtime)
    
    def get_directory_info(self, dir_path: Path) -> dict:
        """获取目录信息"""
        if not dir_path.exists():
            return {"exists": False}
        
        info = {
            "exists": True,
            "name": dir_path.name,
            "path": str(dir_path),
            "created": datetime.fromtimestamp(dir_path.stat().st_ctime),
            "modified": datetime.fromtimestamp(dir_path.stat().st_mtime),
            "media_counts": {}
        }
        
        # 统计各种媒体类型
        media_types = ["images", "gifs", "unknown"]
        if settings.app.enable_video:
            media_types.insert(1, "videos")
        for media_type in media_types:
            media_path = dir_path / media_type
            if media_path.exists():
                info["media_counts"][media_type] = len(list(media_path.glob("*")))
            else:
                info["media_counts"][media_type] = 0
        
        return info
    
    def cleanup_old_directories(self, keep_days: int = 7):
        """清理旧目录，保留指定天数"""
        today = datetime.now()
        
        for dir_path in self.base_dir.iterdir():
            if not dir_path.is_dir():
                continue
            
            try:
                # 目录名形如 YYYY-MM-DD
                dir_date = datetime.strptime(dir_path.name, "%Y-%m-%d")
                # 计算天数差
                days_old = (today - dir_date).days
                if days_old > keep_days:
                    import shutil
                    shutil.rmtree(dir_path)
                    print(f"🗑️ 清理旧目录: {dir_path.name} (已保存 {days_old} 天)")
            except Exception as e:
                print(f"⚠️ 处理目录 {dir_path.name} 时出错: {e}")

# 全局实例
directory_manager = DirectoryManager()

def get_today_directory(posts_count: int = None) -> Path:
    """便捷函数：获取今天的目录"""
    return directory_manager.get_today_directory(posts_count)

def get_media_subdirectory(media_type: str, posts_count: int = None) -> Path:
    """便捷函数：获取媒体子目录"""
    return directory_manager.get_media_subdirectory(media_type, posts_count)

def find_latest_directory() -> Optional[Path]:
    """便捷函数：查找最新目录"""
    return directory_manager.find_latest_directory()
