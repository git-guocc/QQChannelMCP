#!/usr/bin/env python3
"""
测试两种时间筛选功能的区别
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from complete_hellokitty_downloader import CompleteHelloKittyDownloader

def test_both_time_filters():
    """测试两种时间筛选功能的区别"""
    print("🔍 测试两种时间筛选功能的区别...")
    
    # 创建下载器实例
    downloader = CompleteHelloKittyDownloader()
    
    # 模拟一些帖子数据
    class MockPost:
        def __init__(self, title, post_time):
            self.title = title
            self.post_time = post_time
            self.images = ["image1.jpg", "image2.jpg"]  # 模拟图片
    
    # 创建不同时间的测试帖子
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    
    test_posts = [
        MockPost("今天凌晨1点", today_start + timedelta(hours=1)),      # 今天1点
        MockPost("今天早上8点", today_start + timedelta(hours=8)),      # 今天8点
        MockPost("昨天晚上11点", today_start - timedelta(hours=1)),     # 昨天23点
        MockPost("昨天下午2点", today_start - timedelta(hours=10)),     # 昨天14点
        MockPost("23小时前", now - timedelta(hours=23)),               # 23小时前
        MockPost("25小时前", now - timedelta(hours=25)),               # 25小时前
        MockPost("当前时间", now),                                     # 现在
    ]
    
    print(f"\n📅 当前时间: {now}")
    print(f"🌅 今天开始时间: {today_start}")
    
    print(f"\n📝 测试帖子:")
    for i, post in enumerate(test_posts, 1):
        time_diff = now - post.post_time
        hours_diff = time_diff.total_seconds() / 3600
        is_today = today_start <= post.post_time < (today_start + timedelta(days=1))
        
        today_status = "✅ 今天" if is_today else "❌ 非今天"
        print(f"   {i}. {post.title} - 发帖时间: {post.post_time} - {today_status} (相对时间: {hours_diff:+.1f}小时)")
    
    # 测试1: 今天的所有帖子（绝对时间）
    print(f"\n🎯 测试1: 筛选今天的所有帖子（绝对时间）...")
    today_posts = downloader.filter_today_posts(test_posts)
    
    print(f"✅ 今天的帖子筛选结果:")
    print(f"   筛选出: {len(today_posts)}/{len(test_posts)} 个帖子")
    if today_posts:
        for i, post in enumerate(today_posts, 1):
            print(f"      {i}. {post.title} - {post.post_time}")
    
    # 测试2: 最近24小时内的帖子（相对时间）
    print(f"\n🎯 测试2: 筛选最近24小时内的帖子（相对时间）...")
    recent_24h_posts = downloader.filter_recent_hours_posts(test_posts, 24)
    
    print(f"✅ 最近24小时筛选结果:")
    print(f"   筛选出: {len(recent_24h_posts)}/{len(test_posts)} 个帖子")
    if recent_24h_posts:
        for i, post in enumerate(recent_24h_posts, 1):
            time_diff = now - post.post_time
            hours_diff = time_diff.total_seconds() / 3600
            print(f"      {i}. {post.title} - {post.post_time} (相对时间: {hours_diff:+.1f}小时)")
    
    # 测试3: 最近12小时内的帖子（相对时间）
    print(f"\n🎯 测试3: 筛选最近12小时内的帖子（相对时间）...")
    recent_12h_posts = downloader.filter_recent_hours_posts(test_posts, 12)
    
    print(f"✅ 最近12小时筛选结果:")
    print(f"   筛选出: {len(recent_12h_posts)}/{len(test_posts)} 个帖子")
    if recent_12h_posts:
        for i, post in enumerate(recent_12h_posts, 1):
            time_diff = now - post.post_time
            hours_diff = time_diff.total_seconds() / 3600
            print(f"      {i}. {post.title} - {post.post_time} (相对时间: {hours_diff:+.1f}小时)")
    
    # 对比分析
    print(f"\n📊 对比分析:")
    print(f"   今天的所有帖子: {len(today_posts)} 个")
    print(f"   最近24小时内: {len(recent_24h_posts)} 个")
    print(f"   最近12小时内: {len(recent_12h_posts)} 个")
    
    print(f"\n💡 使用场景:")
    print(f"   🗓️  filter_today_posts(): 当你想要'今天发布的所有内容'")
    print(f"   ⏰ filter_recent_hours_posts(24): 当你想要'最新的24小时内容'")
    print(f"   ⚡ filter_recent_hours_posts(12): 当你想要'最新的12小时内容'")
    
    print(f"\n🔍 区别说明:")
    print(f"   今天的所有帖子: 从今天0点开始，到明天0点之前")
    print(f"   最近N小时内: 从现在往前推N小时的时间窗口")

if __name__ == "__main__":
    test_both_time_filters()
