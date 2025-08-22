"""
数据存储模块
"""

from .json_storage import JSONStorage
from .csv_storage import CSVStorage
from .image_storage import ImageStorage

__all__ = ["JSONStorage", "CSVStorage", "ImageStorage"]
