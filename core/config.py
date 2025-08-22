"""
配置管理模块
"""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class QQChannelConfig:
    """QQ频道采集配置类"""
    
    # 浏览器配置
    chrome_path: Optional[str] = None
    chromedriver_path: Optional[str] = None
    headless: bool = True
    page_load_timeout: int = 30
    implicit_wait: int = 10
    
    # 采集配置
    default_max_posts: int = 100
    scroll_pause_time: float = 2.0
    request_delay: float = 1.0
    max_retries: int = 3
    
    # 存储配置
    data_dir: str = "data"
    images_dir: str = "data/images"
    enable_image_download: bool = True
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/qq_channel_collector.log"
    
    # MCP服务器配置
    mcp_port: int = 8000
    mcp_host: str = "localhost"
    
    def __post_init__(self):
        """初始化后处理"""
        # 从环境变量获取配置
        self.chrome_path = os.getenv("CHROME_PATH", self.chrome_path)
        self.chromedriver_path = os.getenv("CHROMEDRIVER_PATH", self.chromedriver_path)
        self.headless = os.getenv("HEADLESS", "true").lower() == "true"
        
        # 创建必要的目录
        Path(self.data_dir).mkdir(exist_ok=True)
        Path(self.images_dir).mkdir(parents=True, exist_ok=True)
        
        if self.log_file:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_env(cls) -> "QQChannelConfig":
        """从环境变量创建配置"""
        return cls()


# 全局配置实例
config = QQChannelConfig.from_env()
