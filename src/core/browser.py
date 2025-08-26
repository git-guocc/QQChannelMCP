"""
浏览器管理模块
"""

import asyncio
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from .exceptions import ScrapingError, ConfigurationError, handle_exception

logger = logging.getLogger(__name__)


class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self, config):
        # 兼容 Settings 或 QQChannelConfig
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

    # 兼容性读取配置项（优先 QQChannelConfig，其次 Settings）
    def _headless(self) -> bool:
        if hasattr(self.config, 'headless'):
            return bool(getattr(self.config, 'headless'))
        if hasattr(self.config, 'scraping') and hasattr(self.config.scraping, 'chrome_headless'):
            return bool(self.config.scraping.chrome_headless)
        if hasattr(self.config, 'chrome_headless'):
            return bool(getattr(self.config, 'chrome_headless'))
        return True

    def _page_load_timeout(self) -> int:
        if hasattr(self.config, 'page_load_timeout'):
            return int(getattr(self.config, 'page_load_timeout'))
        if hasattr(self.config, 'scraping') and hasattr(self.config.scraping, 'chrome_timeout'):
            return int(self.config.scraping.chrome_timeout)
        return 30

    def _implicit_wait(self) -> int:
        if hasattr(self.config, 'implicit_wait'):
            return int(getattr(self.config, 'implicit_wait'))
        return 10

    def _chrome_binary(self) -> Optional[str]:
        if hasattr(self.config, 'chrome_path') and getattr(self.config, 'chrome_path'):
            return getattr(self.config, 'chrome_path')
        import os
        return os.getenv('CHROME_PATH')

    def _chromedriver_path(self) -> Optional[str]:
        if hasattr(self.config, 'chromedriver_path') and getattr(self.config, 'chromedriver_path'):
            return getattr(self.config, 'chromedriver_path')
        import os
        return os.getenv('CHROMEDRIVER_PATH')
    
    @handle_exception
    def create_driver(self) -> webdriver.Chrome:
        """创建Chrome浏览器实例"""
        if self.driver:
            return self.driver
        
        try:
            # 配置Chrome选项
            options = self._get_chrome_options()
            
            # 配置Chrome服务
            service = self._get_chrome_service()
            
            # 创建驱动实例
            self.driver = webdriver.Chrome(service=service, options=options)

            # 启用CDP网络监听（Phase 3）
            try:
                self.driver.execute_cdp_cmd('Network.enable', {})
            except Exception as e:
                logger.debug(f"启用CDP Network失败: {e}")

            # 设置超时
            self.driver.implicitly_wait(self._implicit_wait())
            self.driver.set_page_load_timeout(self._page_load_timeout())

            # 创建等待对象
            self.wait = WebDriverWait(self.driver, self._page_load_timeout())
            
            logger.info("浏览器实例创建成功")
            return self.driver
            
        except WebDriverException as e:
            raise ConfigurationError(f"创建浏览器实例失败: {str(e)}")
    
    def _get_chrome_options(self) -> Options:
        """获取Chrome选项配置"""
        options = Options()
        
        # 基础配置
        if self._headless():
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        # 启用性能日志，便于读取Network事件
        try:
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        except Exception:
            pass
        
        # 设置窗口大小
        options.add_argument("--window-size=1920,1080")
        
        # Chrome路径配置
        chrome_bin = self._chrome_binary()
        if chrome_bin:
            options.binary_location = chrome_bin
            logger.info(f"使用配置的Chrome路径: {chrome_bin}")
        
        return options
    
    def _get_chrome_service(self) -> Optional[Service]:
        """获取Chrome服务配置"""
        try:
            # 优先使用配置的ChromeDriver路径（更稳定、无需联网）
            cfg_path = self._chromedriver_path()
            if cfg_path:
                logger.info(f"使用配置的ChromeDriver: {cfg_path}")
                return Service(cfg_path)
            # 回退到 webdriver-manager 自动下载/管理
            chromedriver_path = ChromeDriverManager().install()
            logger.info(f"使用webdriver-manager安装的ChromeDriver: {chromedriver_path}")
            return Service(chromedriver_path)
        except Exception as e:
            logger.warning(f"无法获取ChromeDriver服务: {e}")
            return None
    
    @handle_exception
    async def navigate_to(self, url: str) -> None:
        """导航到指定URL"""
        if not self.driver:
            self.create_driver()
        
        try:
            logger.info(f"导航到: {url}")
            self.driver.get(url)
            
            # 等待页面加载完成
            await self.wait_for_page_load()
            
        except TimeoutException:
            raise ScrapingError(f"访问页面超时: {url}")
        except Exception as e:
            raise ScrapingError(f"导航失败: {str(e)}")
    
    async def wait_for_page_load(self, timeout: Optional[int] = None) -> bool:
        """等待页面加载完成"""
        if not self.wait:
            return False
        
        try:
            timeout = timeout or self.config.page_load_timeout
            
            # 等待页面就绪状态
            self.wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # 额外等待一段时间确保动态内容加载
            await asyncio.sleep(2)
            
            return True
            
        except TimeoutException:
            logger.warning("页面加载超时")
            return False
    
    @handle_exception
    async def scroll_to_bottom(self, pause_time: Optional[float] = None) -> None:
        """滚动到页面底部"""
        if not self.driver:
            raise ScrapingError("浏览器实例未创建")
        
        pause_time = pause_time or self.config.scroll_pause_time
        
        # 获取初始页面高度
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # 滚动到底部
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # 等待新内容加载
            await asyncio.sleep(pause_time)
            
            # 计算新的页面高度
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # 如果高度没有变化，说明到底了
            if new_height == last_height:
                break
                
            last_height = new_height
    
    @handle_exception
    async def scroll_and_collect(self, max_items: int, item_selector: str) -> list:
        """滚动页面并收集元素"""
        if not self.driver:
            raise ScrapingError("浏览器实例未创建")
        
        collected_items = []
        last_count = 0
        no_change_count = 0
        
        while len(collected_items) < max_items:
            # 滚动页面
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(self.config.scroll_pause_time)
            
            # 查找当前页面的所有项目
            elements = self.driver.find_elements(By.CSS_SELECTOR, item_selector)
            current_count = len(elements)
            
            # 如果没有新内容，增加计数器
            if current_count == last_count:
                no_change_count += 1
                if no_change_count >= 3:  # 连续3次没有新内容就停止
                    break
            else:
                no_change_count = 0
                last_count = current_count
            
            # 更新收集的元素
            collected_items = elements[:max_items]
        
        return collected_items
    
    def find_element_safe(self, by: By, value: str, timeout: int = 5):
        """安全查找元素"""
        try:
            wait = WebDriverWait(self.driver, timeout)
            return wait.until(EC.presence_of_element_located((by, value)))
        except TimeoutException:
            return None
    
    def find_elements_safe(self, by: By, value: str) -> list:
        """安全查找多个元素"""
        try:
            return self.driver.find_elements(by, value)
        except Exception:
            return []
    
    def get_element_text_safe(self, element) -> str:
        """安全获取元素文本"""
        try:
            return element.text.strip() if element else ""
        except Exception:
            return ""
    
    def get_element_attribute_safe(self, element, attribute: str) -> str:
        """安全获取元素属性"""
        try:
            return element.get_attribute(attribute) if element else ""
        except Exception:
            return ""
    
    def close_driver(self) -> None:
        """关闭浏览器实例"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("浏览器实例已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器失败: {e}")
            finally:
                self.driver = None
                self.wait = None
    
    def __enter__(self):
        """上下文管理器入口"""
        self.create_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close_driver()
