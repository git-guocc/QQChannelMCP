"""
HelloKitty频道数据采集工具

专为HelloKitty频道设计的MCP数据采集工具
支持图片、动图、视频的智能识别和分类下载
"""

__version__ = "2.1.0"
__author__ = "HelloKitty MCP Team"
__description__ = "HelloKitty频道多媒体数据采集工具"

# 导入主要组件
from .complete_hellokitty_downloader import CompleteHelloKittyDownloader

__all__ = [
    "CompleteHelloKittyDownloader"
]
