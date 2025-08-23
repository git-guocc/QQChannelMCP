"""
帖子数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import json


@dataclass
class QQChannelPost:
    """QQ频道帖子数据模型"""
    
    # 基础信息
    post_id: str                    # 帖子ID
    channel_id: str                 # 频道ID
    channel_name: str               # 频道名称
    author_name: str                # 作者昵称
    author_id: Optional[str] = None # 作者ID
    
    # 内容信息
    title: Optional[str] = None     # 帖子标题
    content: str = ""               # 文字内容
    images: List[str] = field(default_factory=list)      # 图片URL列表
    image_paths: List[str] = field(default_factory=list) # 本地图片路径
    gifs: List[str] = field(default_factory=list)        # 动图URL列表
    gif_paths: List[str] = field(default_factory=list)   # 本地动图路径
    videos: List[str] = field(default_factory=list)      # 视频URL列表
    video_paths: List[str] = field(default_factory=list) # 本地视频路径
    
    # 时间信息
    post_time: Optional[datetime] = None    # 发布时间
    collected_time: datetime = field(default_factory=datetime.now)  # 采集时间
    
    # 互动数据
    like_count: int = 0             # 点赞数
    comment_count: int = 0          # 评论数
    share_count: int = 0            # 分享数
    view_count: int = 0             # 浏览数
    
    # 链接信息
    post_url: str = ""              # 帖子链接
    
    # 分类信息
    tags: List[str] = field(default_factory=list)  # 标签列表
    post_type: str = "text"         # 帖子类型（text/image/video）
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'post_id': self.post_id,
            'channel_id': self.channel_id,
            'channel_name': self.channel_name,
            'author_name': self.author_name,
            'author_id': self.author_id,
            'title': self.title,
            'content': self.content,
            'images': self.images,
            'image_paths': self.image_paths,
            'images_count': len(self.images),
            'gifs': self.gifs,
            'gif_paths': self.gif_paths,
            'gifs_count': len(self.gifs),
            'videos': self.videos,
            'video_paths': self.video_paths,
            'videos_count': len(self.videos),
            'post_time': self.post_time.isoformat() if self.post_time else None,
            'collected_time': self.collected_time.isoformat(),
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'share_count': self.share_count,
            'view_count': self.view_count,
            'post_url': self.post_url,
            'tags': self.tags,
            'post_type': self.post_type,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QQChannelPost":
        """从字典创建实例"""
        # 处理时间字段
        if data.get('post_time'):
            if isinstance(data['post_time'], str):
                from dateutil.parser import parse
                data['post_time'] = parse(data['post_time'])
        
        if data.get('collected_time'):
            if isinstance(data['collected_time'], str):
                from dateutil.parser import parse
                data['collected_time'] = parse(data['collected_time'])
        
        # 处理列表字段
        data['images'] = data.get('images', [])
        data['image_paths'] = data.get('image_paths', [])
        data['gifs'] = data.get('gifs', [])
        data['gif_paths'] = data.get('gif_paths', [])
        data['videos'] = data.get('videos', [])
        data['video_paths'] = data.get('video_paths', [])
        data['tags'] = data.get('tags', [])
        data['metadata'] = data.get('metadata', {})
        
        return cls(**data)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "QQChannelPost":
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def has_images(self) -> bool:
        """是否包含图片"""
        return len(self.images) > 0
    
    def has_gifs(self) -> bool:
        """是否包含动图"""
        return len(self.gifs) > 0
    
    def has_videos(self) -> bool:
        """是否包含视频"""
        return len(self.videos) > 0
    
    def has_media(self) -> bool:
        """是否包含任何媒体"""
        return self.has_images() or self.has_gifs() or self.has_videos()
    
    def has_content(self) -> bool:
        """是否有有效内容"""
        return bool(self.content.strip() or self.title)
    
    def get_content_length(self) -> int:
        """获取内容长度"""
        total_content = f"{self.title or ''} {self.content}".strip()
        return len(total_content)
    
    def add_image(self, image_url: str, local_path: Optional[str] = None) -> None:
        """添加图片"""
        if image_url and image_url not in self.images:
            self.images.append(image_url)
            if local_path:
                self.image_paths.append(local_path)
    
    def add_gif(self, gif_url: str, local_path: Optional[str] = None) -> None:
        """添加动图"""
        if gif_url and gif_url not in self.gifs:
            self.gifs.append(gif_url)
            if local_path:
                self.gif_paths.append(local_path)
    
    def add_video(self, video_url: str, local_path: Optional[str] = None) -> None:
        """添加视频"""
        if video_url and video_url not in self.videos:
            self.videos.append(video_url)
            if local_path:
                self.video_paths.append(local_path)
    
    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if tag and tag not in self.tags:
            self.tags.append(tag)
    
    def update_metadata(self, key: str, value: Any) -> None:
        """更新元数据"""
        self.metadata[key] = value
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"QQChannelPost(id={self.post_id}, channel={self.channel_name}, author={self.author_name})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"QQChannelPost(post_id='{self.post_id}', "
                f"channel_name='{self.channel_name}', "
                f"author_name='{self.author_name}', "
                f"content_length={self.get_content_length()}, "
                f"images_count={len(self.images)})")


@dataclass
class PostCollection:
    """帖子集合类"""
    
    posts: List[QQChannelPost] = field(default_factory=list)
    channel_name: str = ""
    collected_time: datetime = field(default_factory=datetime.now)
    total_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_post(self, post: QQChannelPost) -> None:
        """添加帖子"""
        self.posts.append(post)
        self.total_count = len(self.posts)
    
    def get_posts_by_author(self, author_name: str) -> List[QQChannelPost]:
        """根据作者筛选帖子"""
        return [post for post in self.posts if post.author_name == author_name]
    
    def get_posts_with_images(self) -> List[QQChannelPost]:
        """获取包含图片的帖子"""
        return [post for post in self.posts if post.has_images()]
    
    def get_posts_with_gifs(self) -> List[QQChannelPost]:
        """获取包含动图的帖子"""
        return [post for post in self.posts if post.has_gifs()]
    
    def get_posts_with_videos(self) -> List[QQChannelPost]:
        """获取包含视频的帖子"""
        return [post for post in self.posts if post.has_videos()]
    
    def get_posts_with_media(self) -> List[QQChannelPost]:
        """获取包含任何媒体的帖子"""
        return [post for post in self.posts if post.has_media()]
    
    def get_posts_by_type(self, post_type: str) -> List[QQChannelPost]:
        """根据类型筛选帖子"""
        return [post for post in self.posts if post.post_type == post_type]
    
    def sort_by_time(self, reverse: bool = True) -> None:
        """按时间排序"""
        self.posts.sort(
            key=lambda x: x.post_time or datetime.min, 
            reverse=reverse
        )
    
    def sort_by_likes(self, reverse: bool = True) -> None:
        """按点赞数排序"""
        self.posts.sort(key=lambda x: x.like_count, reverse=reverse)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'channel_name': self.channel_name,
            'collected_time': self.collected_time.isoformat(),
            'total_count': self.total_count,
            'posts': [post.to_dict() for post in self.posts],
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PostCollection":
        """从字典创建实例"""
        if data.get('collected_time') and isinstance(data['collected_time'], str):
            from dateutil.parser import parse
            data['collected_time'] = parse(data['collected_time'])
        
        posts = [QQChannelPost.from_dict(post_data) for post_data in data.get('posts', [])]
        
        collection = cls(
            posts=posts,
            channel_name=data.get('channel_name', ''),
            collected_time=data.get('collected_time', datetime.now()),
            total_count=data.get('total_count', len(posts)),
            metadata=data.get('metadata', {})
        )
        
        return collection
