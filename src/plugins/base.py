#!/usr/bin/env python3
"""
插件系统基础框架
支持插件的动态加载、管理和生命周期管理
"""

import os
import sys
import importlib
import logging
import asyncio
from typing import Dict, List, Any, Optional, Type, Callable, Union
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import json
import yaml

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    version: str
    description: str
    author: str
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    python_version: str = ">=3.8"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


@dataclass
class PluginInfo:
    """插件信息"""
    metadata: PluginMetadata
    plugin_class: Type
    plugin_instance: Any
    is_enabled: bool = True
    is_loaded: bool = False
    load_time: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None


class BasePlugin(ABC):
    """插件基类"""
    
    def __init__(self):
        self.metadata: Optional[PluginMetadata] = None
        self.plugin_id: str = ""
        self.is_initialized: bool = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """启动插件"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """停止插件"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置模式"""
        return {}
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        return True
    
    def get_dependencies(self) -> List[str]:
        """获取依赖列表"""
        return self.metadata.dependencies if self.metadata else []
    
    def get_requirements(self) -> List[str]:
        """获取Python包依赖"""
        return []


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, PluginInfo] = {}
        self.plugin_loaders: Dict[str, Callable] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        
        # 插件类型注册
        self.plugin_types: Dict[str, Type[BasePlugin]] = {}
        
        # 统计信息
        self.stats = {
            "total_plugins": 0,
            "loaded_plugins": 0,
            "enabled_plugins": 0,
            "failed_plugins": 0
        }
        
        # 确保插件目录存在
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # 注册默认插件类型
        self._register_default_plugin_types()
    
    def _register_default_plugin_types(self):
        """注册默认插件类型"""
        # 这里可以注册一些基础的插件类型
        pass
    
    def register_plugin_type(self, plugin_type: str, base_class: Type[BasePlugin]):
        """注册插件类型"""
        self.plugin_types[plugin_type] = base_class
        logger.info(f"插件类型已注册: {plugin_type} -> {base_class.__name__}")
    
    def discover_plugins(self) -> List[str]:
        """发现插件"""
        discovered_plugins = []
        
        for plugin_path in self.plugins_dir.rglob("*.py"):
            if plugin_path.name.startswith("__"):
                continue
            
            try:
                # 尝试导入插件模块
                module_path = plugin_path.relative_to(self.plugins_dir)
                module_name = str(module_path).replace("/", ".").replace("\\", ".").replace(".py", "")
                
                if module_name not in discovered_plugins:
                    discovered_plugins.append(module_name)
                    
            except Exception as e:
                logger.warning(f"发现插件失败: {plugin_path}, 错误: {e}")
        
        logger.info(f"发现 {len(discovered_plugins)} 个插件")
        return discovered_plugins
    
    async def load_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """加载插件"""
        try:
            if plugin_name in self.plugins:
                logger.warning(f"插件已存在: {plugin_name}")
                return False
            
            # 构建模块路径
            module_path = f"plugins.{plugin_name}"
            
            # 导入插件模块
            try:
                module = importlib.import_module(module_path)
            except ImportError as e:
                logger.error(f"导入插件模块失败: {plugin_name}, 错误: {e}")
                return False
            
            # 查找插件类
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BasePlugin) and 
                    attr != BasePlugin):
                    plugin_class = attr
                    break
            
            if not plugin_class:
                logger.error(f"未找到插件类: {plugin_name}")
                return False
            
            # 创建插件实例
            plugin_instance = plugin_class()
            
            # 设置插件ID
            plugin_instance.plugin_id = plugin_name
            
            # 加载配置
            if config:
                plugin_config = config
            else:
                plugin_config = self._load_plugin_config(plugin_name)
            
            # 验证配置
            if not plugin_instance.validate_config(plugin_config):
                logger.error(f"插件配置验证失败: {plugin_name}")
                return False
            
            # 初始化插件
            if not await plugin_instance.initialize():
                logger.error(f"插件初始化失败: {plugin_name}")
                return False
            
            # 创建插件信息
            plugin_info = PluginInfo(
                metadata=plugin_instance.metadata or self._create_default_metadata(plugin_name),
                plugin_class=plugin_class,
                plugin_instance=plugin_instance,
                is_enabled=True,
                is_loaded=True,
                load_time=datetime.now()
            )
            
            # 注册插件
            self.plugins[plugin_name] = plugin_info
            self.plugin_configs[plugin_name] = plugin_config
            
            # 更新统计
            self.stats["total_plugins"] += 1
            self.stats["loaded_plugins"] += 1
            self.stats["enabled_plugins"] += 1
            
            logger.info(f"插件加载成功: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"插件加载失败: {plugin_name}, 错误: {e}")
            self.stats["failed_plugins"] += 1
            return False
    
    def _load_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """加载插件配置"""
        config_paths = [
            self.plugins_dir / f"{plugin_name}.json",
            self.plugins_dir / f"{plugin_name}.yaml",
            self.plugins_dir / f"{plugin_name}.yml",
            self.plugins_dir / plugin_name / "config.json",
            self.plugins_dir / plugin_name / "config.yaml",
            self.plugins_dir / plugin_name / "config.yml"
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    if config_path.suffix == ".json":
                        with open(config_path, 'r', encoding='utf-8') as f:
                            return json.load(f)
                    elif config_path.suffix in [".yaml", ".yml"]:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            return yaml.safe_load(f)
                except Exception as e:
                    logger.warning(f"加载插件配置失败: {config_path}, 错误: {e}")
        
        return {}
    
    def _create_default_metadata(self, plugin_name: str) -> PluginMetadata:
        """创建默认元数据"""
        return PluginMetadata(
            name=plugin_name,
            version="1.0.0",
            description=f"Plugin: {plugin_name}",
            author="Unknown",
            tags=["auto-generated"]
        )
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        if plugin_name not in self.plugins:
            logger.warning(f"插件不存在: {plugin_name}")
            return False
        
        try:
            plugin_info = self.plugins[plugin_name]
            
            # 停止插件
            if plugin_info.is_enabled:
                await plugin_info.plugin_instance.stop()
            
            # 移除插件
            del self.plugins[plugin_name]
            if plugin_name in self.plugin_configs:
                del self.plugin_configs[plugin_name]
            
            # 更新统计
            self.stats["total_plugins"] -= 1
            self.stats["loaded_plugins"] -= 1
            if plugin_info.is_enabled:
                self.stats["enabled_plugins"] -= 1
            
            logger.info(f"插件卸载成功: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"插件卸载失败: {plugin_name}, 错误: {e}")
            return False
    
    async def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        if plugin_name not in self.plugins:
            logger.error(f"插件不存在: {plugin_name}")
            return False
        
        try:
            plugin_info = self.plugins[plugin_name]
            
            if plugin_info.is_enabled:
                logger.info(f"插件已启用: {plugin_name}")
                return True
            
            # 启动插件
            if await plugin_info.plugin_instance.start():
                plugin_info.is_enabled = True
                self.stats["enabled_plugins"] += 1
                logger.info(f"插件启用成功: {plugin_name}")
                return True
            else:
                logger.error(f"插件启动失败: {plugin_name}")
                return False
                
        except Exception as e:
            logger.error(f"插件启用失败: {plugin_name}, 错误: {e}")
            return False
    
    async def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        if plugin_name not in self.plugins:
            logger.error(f"插件不存在: {plugin_name}")
            return False
        
        try:
            plugin_info = self.plugins[plugin_name]
            
            if not plugin_info.is_enabled:
                logger.info(f"插件已禁用: {plugin_name}")
                return True
            
            # 停止插件
            if await plugin_info.plugin_instance.stop():
                plugin_info.is_enabled = False
                self.stats["enabled_plugins"] -= 1
                logger.info(f"插件禁用成功: {plugin_name}")
                return True
            else:
                logger.error(f"插件停止失败: {plugin_name}")
                return False
                
        except Exception as e:
            logger.error(f"插件禁用失败: {plugin_name}, 错误: {e}")
            return False
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        try:
            # 卸载插件
            if not await self.unload_plugin(plugin_name):
                return False
            
            # 重新加载插件
            return await self.load_plugin(plugin_name)
            
        except Exception as e:
            logger.error(f"插件重载失败: {plugin_name}, 错误: {e}")
            return False
    
    async def health_check_all(self) -> Dict[str, Any]:
        """检查所有插件健康状态"""
        health_results = {}
        
        for plugin_name, plugin_info in self.plugins.items():
            try:
                if plugin_info.is_enabled:
                    health = await plugin_info.plugin_instance.health_check()
                    health_results[plugin_name] = {
                        "status": "healthy",
                        "health": health,
                        "enabled": True
                    }
                else:
                    health_results[plugin_name] = {
                        "status": "disabled",
                        "enabled": False
                    }
            except Exception as e:
                health_results[plugin_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "enabled": plugin_info.is_enabled
                }
                plugin_info.error_count += 1
                plugin_info.last_error = str(e)
        
        return health_results
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginInfo]:
        """获取所有插件"""
        return self.plugins.copy()
    
    def get_enabled_plugins(self) -> Dict[str, PluginInfo]:
        """获取已启用的插件"""
        return {name: info for name, info in self.plugins.items() if info.is_enabled}
    
    def get_plugin_stats(self) -> Dict[str, Any]:
        """获取插件统计信息"""
        return {
            **self.stats,
            "plugin_names": list(self.plugins.keys()),
            "enabled_names": list(self.get_enabled_plugins().keys())
        }
    
    async def shutdown(self):
        """关闭插件管理器"""
        logger.info("正在关闭插件管理器...")
        
        # 停止所有启用的插件
        for plugin_name, plugin_info in self.plugins.items():
            if plugin_info.is_enabled:
                try:
                    await plugin_info.plugin_instance.stop()
                    logger.info(f"插件已停止: {plugin_name}")
                except Exception as e:
                    logger.error(f"停止插件失败: {plugin_name}, 错误: {e}")
        
        logger.info("插件管理器已关闭")


# 全局插件管理器实例
plugin_manager = PluginManager()


# 插件装饰器
def plugin(plugin_type: str = "generic"):
    """插件装饰器"""
    def decorator(cls):
        if not issubclass(cls, BasePlugin):
            raise TypeError(f"类 {cls.__name__} 必须继承自 BasePlugin")
        
        # 注册插件类型
        plugin_manager.register_plugin_type(plugin_type, cls)
        
        # 设置插件类型
        cls.plugin_type = plugin_type
        
        return cls
    return decorator


# 插件类型定义
class ScraperPlugin(BasePlugin):
    """采集器插件基类"""
    
    @abstractmethod
    async def scrape(self, url: str, **kwargs) -> List[Any]:
        """执行采集"""
        pass
    
    @abstractmethod
    def supports_url(self, url: str) -> bool:
        """检查是否支持该URL"""
        pass


class RecognizerPlugin(BasePlugin):
    """识别器插件基类"""
    
    @abstractmethod
    async def recognize(self, data: Any, **kwargs) -> Dict[str, Any]:
        """执行识别"""
        pass
    
    @abstractmethod
    def supports_data_type(self, data_type: str) -> bool:
        """检查是否支持该数据类型"""
        pass


class ProcessorPlugin(BasePlugin):
    """处理器插件基类"""
    
    @abstractmethod
    async def process(self, data: Any, **kwargs) -> Any:
        """执行处理"""
        pass
    
    @abstractmethod
    def supports_data_type(self, data_type: str) -> bool:
        """检查是否支持该数据类型"""
        pass


class ExporterPlugin(BasePlugin):
    """导出器插件基类"""
    
    @abstractmethod
    async def export(self, data: Any, **kwargs) -> bool:
        """执行导出"""
        pass
    
    @abstractmethod
    def supports_format(self, format_name: str) -> bool:
        """检查是否支持该格式"""
        pass
