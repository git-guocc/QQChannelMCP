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
    data_dir: str = "/home/guocc/GitHub/MCP/QQChannelMCP/data"
    dayupdate_dir: str = "/home/guocc/GitHub/MCP/QQChannelMCP/data/dayupdate"
    enable_image_download: bool = True
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/qq_channel_collector.log"
    
    # MCP服务器配置
    mcp_port: int = 8000
    mcp_host: str = "localhost"
    
    # AI API配置
    gemini_api_key: Optional[str] = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    github_models_api_key: Optional[str] = None
    github_models_base_url: str = "https://models.github.ai"
    cherrystudio_api_key: Optional[str] = None
    cherrystudio_base_url: str = "https://api.cherrystudio.ai"
    ai_preferred_provider: str = "cherrystudio"
    
    def __post_init__(self):
        """初始化后处理"""
        # 从环境变量获取配置
        self.chrome_path = os.getenv("CHROME_PATH", self.chrome_path)
        self.chromedriver_path = os.getenv("CHROMEDRIVER_PATH", self.chromedriver_path)
        self.headless = os.getenv("HEADLESS", "true").lower() == "true"
        
        # AI API配置
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", self.gemini_api_key)
        self.gemini_base_url = os.getenv("GEMINI_BASE_URL", self.gemini_base_url)
        self.github_models_api_key = os.getenv("GITHUB_MODELS_API_KEY", self.github_models_api_key)
        self.github_models_base_url = os.getenv("GITHUB_MODELS_BASE_URL", self.github_models_base_url)
        self.cherrystudio_api_key = os.getenv("CHERRYSTUDIO_API_KEY", self.cherrystudio_api_key)
        self.cherrystudio_base_url = os.getenv("CHERRYSTUDIO_BASE_URL", self.cherrystudio_base_url)
        self.ai_preferred_provider = os.getenv("AI_PREFERRED_PROVIDER", self.ai_preferred_provider)
        
        # 创建必要的目录
        Path(self.data_dir).mkdir(exist_ok=True)
        Path(self.dayupdate_dir).mkdir(parents=True, exist_ok=True)
        
        if self.log_file:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_env(cls) -> "QQChannelConfig":
        """从环境变量创建配置"""
        return cls()


# 全局配置实例
config = QQChannelConfig.from_env()
