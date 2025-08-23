"""
频道数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import json


@dataclass
class QQChannel:
    """QQ频道数据模型"""
    
    # 基础信息
    channel_id: str                 # 频道ID
    channel_name: str               # 频道名称
    channel_url: str                # 频道链接
    description: str = ""           # 频道描述
    
    # 统计信息
    member_count: int = 0           # 成员数量
    post_count: int = 0             # 帖子数量
    online_count: int = 0           # 在线人数
    
    # 分类信息
    category: str = ""              # 频道分类
    tags: List[str] = field(default_factory=list)  # 频道标签
    
    # 管理信息
    owner_name: str = ""            # 频道主名称
    admins: List[str] = field(default_factory=list)  # 管理员列表
    
    # 时间信息
    created_time: Optional[datetime] = None   # 创建时间
    last_active_time: Optional[datetime] = None  # 最后活跃时间
    discovered_time: datetime = field(default_factory=datetime.now)  # 发现时间
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'channel_id': self.channel_id,
            'channel_name': self.channel_name,
            'channel_url': self.channel_url,
            'description': self.description,
            'member_count': self.member_count,
            'post_count': self.post_count,
            'online_count': self.online_count,
            'category': self.category,
            'tags': self.tags,
            'owner_name': self.owner_name,
            'admins': self.admins,
            'created_time': self.created_time.isoformat() if self.created_time else None,
            'last_active_time': self.last_active_time.isoformat() if self.last_active_time else None,
            'discovered_time': self.discovered_time.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QQChannel":
        """从字典创建实例"""
        # 处理时间字段
        time_fields = ['created_time', 'last_active_time', 'discovered_time']
        for field_name in time_fields:
            if data.get(field_name) and isinstance(data[field_name], str):
                from dateutil.parser import parse
                data[field_name] = parse(data[field_name])
        
        # 处理列表字段
        data['tags'] = data.get('tags', [])
        data['admins'] = data.get('admins', [])
        data['metadata'] = data.get('metadata', {})
        
        return cls(**data)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "QQChannel":
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if tag and tag not in self.tags:
            self.tags.append(tag)
    
    def add_admin(self, admin_name: str) -> None:
        """添加管理员"""
        if admin_name and admin_name not in self.admins:
            self.admins.append(admin_name)
    
    def update_metadata(self, key: str, value: Any) -> None:
        """更新元数据"""
        self.metadata[key] = value
    
    def is_active(self, hours: int = 24) -> bool:
        """判断频道是否活跃"""
        if not self.last_active_time:
            return False
        
        time_diff = datetime.now() - self.last_active_time
        return time_diff.total_seconds() < hours * 3600
    
    def get_activity_level(self) -> str:
        """获取活跃度级别"""
        if self.is_active(24):
            return "高"
        elif self.is_active(24 * 7):  # 一周
            return "中"
        elif self.is_active(24 * 30):  # 一月
            return "低"
        else:
            return "不活跃"
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"QQChannel(name={self.channel_name}, members={self.member_count})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"QQChannel(channel_id='{self.channel_id}', "
                f"channel_name='{self.channel_name}', "
                f"member_count={self.member_count}, "
                f"post_count={self.post_count})")


@dataclass 
class ChannelStats:
    """频道统计信息"""
    
    channel_id: str
    channel_name: str
    
    # 基础统计
    total_posts: int = 0
    total_members: int = 0
    active_members: int = 0
    
    # 内容统计
    text_posts: int = 0
    image_posts: int = 0
    video_posts: int = 0
    
    # 互动统计
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    
    # 时间统计
    stats_time: datetime = field(default_factory=datetime.now)
    last_post_time: Optional[datetime] = None
    
    # 热门内容
    top_posts: List[str] = field(default_factory=list)  # 热门帖子ID列表
    active_authors: List[str] = field(default_factory=list)  # 活跃作者列表
    
    def get_engagement_rate(self) -> float:
        """计算互动率"""
        if self.total_posts == 0:
            return 0.0
        
        total_interactions = self.total_likes + self.total_comments + self.total_shares
        return total_interactions / self.total_posts
    
    def get_avg_likes_per_post(self) -> float:
        """计算平均点赞数"""
        if self.total_posts == 0:
            return 0.0
        return self.total_likes / self.total_posts
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'channel_id': self.channel_id,
            'channel_name': self.channel_name,
            'total_posts': self.total_posts,
            'total_members': self.total_members,
            'active_members': self.active_members,
            'text_posts': self.text_posts,
            'image_posts': self.image_posts,
            'video_posts': self.video_posts,
            'total_likes': self.total_likes,
            'total_comments': self.total_comments,
            'total_shares': self.total_shares,
            'engagement_rate': self.get_engagement_rate(),
            'avg_likes_per_post': self.get_avg_likes_per_post(),
            'stats_time': self.stats_time.isoformat(),
            'last_post_time': self.last_post_time.isoformat() if self.last_post_time else None,
            'top_posts': self.top_posts,
            'active_authors': self.active_authors
        }
