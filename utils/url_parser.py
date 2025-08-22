"""
URL解析工具
"""

import re
import logging
from urllib.parse import urlparse, parse_qs, unquote
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class URLParser:
    """URL解析器"""
    
    def __init__(self):
        # QQ频道URL模式
        self.qq_channel_patterns = [
            r'https?://pd\.qq\.com/s/([a-zA-Z0-9_-]+)',  # 标准QQ频道URL
            r'https?://qun\.qq\.com/qqweb/qunpro/share\?_wv=3&_wwv=128&appChannel=share&inviteCode=([a-zA-Z0-9_-]+)',
            r'https?://channels\.qq\.com/([a-zA-Z0-9_-]+)',
        ]
    
    def parse_qq_channel_url(self, url: str) -> Dict[str, Any]:
        """
        解析QQ频道URL
        
        Args:
            url: QQ频道URL
            
        Returns:
            解析结果字典
        """
        try:
            if not url:
                return {"valid": False, "error": "URL为空"}
            
            # 清理URL
            url = url.strip()
            
            # 解析基本URL信息
            parsed = urlparse(url)
            
            result = {
                "valid": False,
                "original_url": url,
                "scheme": parsed.scheme,
                "hostname": parsed.hostname,
                "path": parsed.path,
                "query_params": parse_qs(parsed.query),
                "channel_id": None,
                "channel_type": None
            }
            
            # 尝试匹配QQ频道模式
            for i, pattern in enumerate(self.qq_channel_patterns):
                match = re.search(pattern, url)
                if match:
                    result["valid"] = True
                    result["channel_id"] = match.group(1)
                    result["channel_type"] = self._get_channel_type(i, parsed.hostname)
                    result["pattern_matched"] = i
                    break
            
            if not result["valid"]:
                result["error"] = "不是有效的QQ频道URL"
            
            return result
            
        except Exception as e:
            logger.error(f"解析QQ频道URL失败: {e}")
            return {
                "valid": False,
                "error": f"URL解析错误: {str(e)}"
            }
    
    def _get_channel_type(self, pattern_index: int, hostname: str) -> str:
        """根据模式索引和主机名确定频道类型"""
        if pattern_index == 0:
            return "pd_channel"  # pd.qq.com频道
        elif pattern_index == 1:
            return "qun_channel"  # 群聊频道
        elif pattern_index == 2:
            return "channels_qq"  # channels.qq.com
        else:
            return "unknown"
    
    def extract_channel_id(self, url: str) -> Optional[str]:
        """
        提取频道ID
        
        Args:
            url: QQ频道URL
            
        Returns:
            频道ID或None
        """
        result = self.parse_qq_channel_url(url)
        return result.get("channel_id") if result.get("valid") else None
    
    def is_valid_qq_channel_url(self, url: str) -> bool:
        """
        检查是否为有效的QQ频道URL
        
        Args:
            url: 待检查的URL
            
        Returns:
            是否有效
        """
        result = self.parse_qq_channel_url(url)
        return result.get("valid", False)
    
    def normalize_url(self, url: str) -> str:
        """
        标准化URL
        
        Args:
            url: 原始URL
            
        Returns:
            标准化后的URL
        """
        try:
            if not url:
                return ""
            
            # 移除多余的空白字符
            url = url.strip()
            
            # 如果没有协议，添加https
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # 解析并重构URL
            parsed = urlparse(url)
            
            # 移除常见的跟踪参数
            query_params = parse_qs(parsed.query)
            tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']
            
            for param in tracking_params:
                query_params.pop(param, None)
            
            # 重构查询字符串
            from urllib.parse import urlencode
            clean_query = urlencode(query_params, doseq=True)
            
            # 重构URL
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean_query:
                clean_url += f"?{clean_query}"
            
            return clean_url
            
        except Exception as e:
            logger.warning(f"URL标准化失败: {e}")
            return url
    
    def extract_share_info(self, url: str) -> Dict[str, Any]:
        """
        提取分享信息
        
        Args:
            url: 分享URL
            
        Returns:
            分享信息字典
        """
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            share_info = {
                "has_share_info": False,
                "invite_code": None,
                "app_channel": None,
                "source": None
            }
            
            # 提取邀请码
            if 'inviteCode' in query_params:
                share_info["invite_code"] = query_params['inviteCode'][0]
                share_info["has_share_info"] = True
            
            # 提取应用渠道
            if 'appChannel' in query_params:
                share_info["app_channel"] = query_params['appChannel'][0]
            
            # 提取来源
            if 'utm_source' in query_params:
                share_info["source"] = query_params['utm_source'][0]
            elif 'from' in query_params:
                share_info["source"] = query_params['from'][0]
            
            return share_info
            
        except Exception as e:
            logger.error(f"提取分享信息失败: {e}")
            return {"has_share_info": False, "error": str(e)}
    
    def build_direct_url(self, channel_id: str, channel_type: str = "pd_channel") -> str:
        """
        构建直接访问URL
        
        Args:
            channel_id: 频道ID
            channel_type: 频道类型
            
        Returns:
            直接访问URL
        """
        try:
            if channel_type == "pd_channel":
                return f"https://pd.qq.com/s/{channel_id}"
            elif channel_type == "channels_qq":
                return f"https://channels.qq.com/{channel_id}"
            else:
                # 默认使用pd.qq.com
                return f"https://pd.qq.com/s/{channel_id}"
                
        except Exception as e:
            logger.error(f"构建直接URL失败: {e}")
            return ""
    
    def get_url_info(self, url: str) -> Dict[str, Any]:
        """
        获取URL的完整信息
        
        Args:
            url: 目标URL
            
        Returns:
            URL信息字典
        """
        try:
            # 基本解析
            channel_info = self.parse_qq_channel_url(url)
            
            # 分享信息
            share_info = self.extract_share_info(url)
            
            # 标准化URL
            normalized_url = self.normalize_url(url)
            
            return {
                "original_url": url,
                "normalized_url": normalized_url,
                "channel_info": channel_info,
                "share_info": share_info,
                "is_valid": channel_info.get("valid", False)
            }
            
        except Exception as e:
            logger.error(f"获取URL信息失败: {e}")
            return {
                "original_url": url,
                "error": str(e),
                "is_valid": False
            }
