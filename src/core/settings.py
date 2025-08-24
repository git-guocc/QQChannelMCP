#!/usr/bin/env python3
"""
统一配置管理
集中管理所有配置项，支持环境变量、配置文件、默认值
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class Environment(Enum):
    """环境枚举"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class AISettings:
    """AI服务配置"""
    preferred_provider: str = "openrouter"
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    github_models_api_key: str = ""
    github_models_base_url: str = "https://api.github.com/models"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    cherrystudio_api_key: str = ""
    cherrystudio_base_url: str = "https://api.cherrystudio.com"
    
    # AI模型配置
    openrouter_model: str = "openai/gpt-4o-mini"
    gemini_model: str = "gemini-1.5-pro"
    github_model: str = "gpt-4o"
    
    # 请求配置
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 30

@dataclass
class ScrapingSettings:
    """数据采集配置"""
    max_posts: int = 50
    max_retries: int = 3
    retry_delay: float = 1.0
    request_timeout: int = 30
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Chrome配置
    chrome_headless: bool = True
    chrome_timeout: int = 30
    chrome_user_data_dir: Optional[str] = None

@dataclass
class StorageSettings:
    """存储配置"""
    base_directory: str = "data"
    dayupdate_pattern: str = "{count}_posts_{date}"
    image_formats: list = field(default_factory=lambda: ["jpg", "jpeg", "png", "gif", "webp", "avif"])
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    # 目录结构
    images_dir: str = "images"
    gifs_dir: str = "gifs"
    videos_dir: str = "videos"
    hellokitty_dir: str = "HelloKitty"

@dataclass
class LoggingSettings:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    console_enabled: bool = True
    log_file: str = "logs/qqchannel_mcp.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

@dataclass
class AppSettings:
    """应用主配置"""
    name: str = "QQChannelMCP"
    version: str = "1.0.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # 功能开关
    enable_hellokitty_recognition: bool = True
    enable_incremental_update: bool = True
    enable_image_optimization: bool = True
    
    # 性能配置
    max_concurrent_downloads: int = 10
    max_concurrent_ai_requests: int = 5
    batch_size: int = 100

class Settings:
    """统一配置管理器"""
    
    def __init__(self):
        self._load_from_env()
        self._validate_settings()
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        # AI配置
        self.ai = AISettings(
            preferred_provider=os.getenv("AI_PREFERRED_PROVIDER", "openrouter"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"),
            github_models_api_key=os.getenv("GITHUB_MODELS_API_KEY", ""),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            cherrystudio_api_key=os.getenv("CHERRYSTUDIO_API_KEY", ""),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "2048")),
            temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
            timeout=int(os.getenv("AI_TIMEOUT", "30"))
        )
        
        # 采集配置
        self.scraping = ScrapingSettings(
            max_posts=int(os.getenv("MAX_POSTS", "50")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("RETRY_DELAY", "1.0")),
            chrome_headless=os.getenv("CHROME_HEADLESS", "true").lower() == "true"
        )
        
        # 存储配置
        self.storage = StorageSettings(
            base_directory=os.getenv("STORAGE_BASE_DIR", "data"),
            max_file_size=int(os.getenv("MAX_FILE_SIZE", str(100 * 1024 * 1024)))
        )
        
        # 日志配置
        self.logging = LoggingSettings(
            level=os.getenv("LOG_LEVEL", "INFO"),
            file_enabled=os.getenv("LOG_FILE_ENABLED", "true").lower() == "true"
        )
        
        # 应用配置
        self.app = AppSettings(
            environment=Environment(os.getenv("ENVIRONMENT", "development")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            max_concurrent_downloads=int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "10")),
            max_concurrent_ai_requests=int(os.getenv("MAX_CONCURRENT_AI_REQUESTS", "5"))
        )
    
    def _validate_settings(self):
        """验证配置有效性"""
        # 验证AI配置
        if self.ai.preferred_provider == "openrouter" and not self.ai.openrouter_api_key:
            logger.warning("OpenRouter API密钥未设置，将使用备用提供商")
        
        if self.ai.preferred_provider == "gemini" and not self.ai.gemini_api_key:
            logger.warning("Gemini API密钥未设置，将使用备用提供商")
        
        # 验证存储目录
        storage_path = Path(self.storage.base_directory)
        if not storage_path.exists():
            storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建存储目录: {storage_path}")
        
        # 验证日志目录
        if self.logging.file_enabled:
            log_path = Path(self.logging.log_file).parent
            log_path.mkdir(parents=True, exist_ok=True)
    
    def get_ai_client_config(self, provider: str = None) -> Dict[str, Any]:
        """获取指定AI提供商的配置"""
        provider = provider or self.ai.preferred_provider
        
        if provider == "gemini":
            return {
                "api_key": self.ai.gemini_api_key,
                "base_url": self.ai.gemini_base_url,
                "model": self.ai.gemini_model,
                "max_tokens": self.ai.max_tokens,
                "temperature": self.ai.temperature,
                "timeout": self.ai.timeout
            }
        elif provider == "openrouter":
            return {
                "api_key": self.ai.openrouter_api_key,
                "base_url": self.ai.openrouter_base_url,
                "model": self.ai.openrouter_model,
                "max_tokens": self.ai.max_tokens,
                "temperature": self.ai.temperature,
                "timeout": self.ai.timeout
            }
        elif provider == "github_models":
            return {
                "api_key": self.ai.github_models_api_key,
                "base_url": self.ai.github_models_base_url,
                "model": self.ai.github_model,
                "max_tokens": self.ai.max_tokens,
                "temperature": self.ai.temperature,
                "timeout": self.ai.timeout
            }
        else:
            raise ValueError(f"不支持的AI提供商: {provider}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "ai": {
                "preferred_provider": self.ai.preferred_provider,
                "models": {
                    "openrouter": self.ai.openrouter_model,
                    "gemini": self.ai.gemini_model,
                    "github": self.ai.github_model
                },
                "max_tokens": self.ai.max_tokens,
                "temperature": self.ai.temperature
            },
            "scraping": {
                "max_posts": self.scraping.max_posts,
                "max_retries": self.scraping.max_retries,
                "chrome_headless": self.scraping.chrome_headless
            },
            "storage": {
                "base_directory": self.storage.base_directory,
                "max_file_size": self.storage.max_file_size
            },
            "app": {
                "environment": self.app.environment.value,
                "debug": self.app.debug,
                "max_concurrent_downloads": self.app.max_concurrent_downloads
            }
        }
    
    def print_summary(self):
        """打印配置摘要"""
        print("\n" + "="*60)
        print("🔧 QQChannelMCP 配置摘要")
        print("="*60)
        
        config_dict = self.to_dict()
        for section, settings in config_dict.items():
            print(f"\n📋 {section.upper()}:")
            for key, value in settings.items():
                if key == "api_key" and value:
                    print(f"  {key}: {'*' * 8}...")
                else:
                    print(f"  {key}: {value}")
        
        print("="*60)

# 全局配置实例
settings = Settings()
