#!/usr/bin/env python3
"""
测试时间逻辑分离设计
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from complete_hellokitty_downloader import CompleteHelloKittyDownloader

def test_time_logic_separation():
    """测试时间逻辑分离设计"""
    print("🔍 测试时间逻辑分离设计...")
    
    # 创建下载器实例
    downloader = CompleteHelloKittyDownloader()
    
    # 模拟帖子数据 - 包含真实时间和相对时间字符串
    class MockPost:
        def __init__(self, title, post_time, post_time_str):
            self.title = title
            self.post_time = post_time  # 真实时间，用于逻辑处理
            self.post_time_str = post_time_str  # 相对时间字符串，用于展示
            self.images = ["image1.jpg"]
    
    # 创建测试帖子
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    
    test_posts = [
        MockPost("今天凌晨1点", today_start + timedelta(hours=1), "23小时前"),
        MockPost("今天早上8点", today_start + timedelta(hours=8), "1小时前"),
        MockPost("昨天晚上11点", today_start - timedelta(hours=1), "25小时前"),
        MockPost("昨天下午2点", today_start - timedelta(hours=10), "34小时前"),
        MockPost("缺少时间的帖子", None, "未知时间"),
    ]
    
    print(f"\n📅 当前时间: {now}")
    print(f"🌅 今天开始时间: {today_start}")
    
    print(f"\n📝 测试帖子:")
    for i, post in enumerate(test_posts, 1):
        if post.post_time:
            time_diff = now - post.post_time
            hours_diff = time_diff.total_seconds() / 3600
            is_today = today_start <= post.post_time < (today_start + timedelta(days=1))
            today_status = "✅ 今天" if is_today else "❌ 非今天"
            print(f"   {i}. {post.title}")
            print(f"      真实时间: {post.post_time}")
            print(f"      相对时间: {post.post_time_str}")
            print(f"      时间差: {hours_diff:+.1f}小时")
            print(f"      今天状态: {today_status}")
        else:
            print(f"   {i}. {post.title}")
            print(f"      真实时间: 无")
            print(f"      相对时间: {post.post_time_str}")
            print(f"      时间差: 无法计算")
            print(f"      今天状态: 无法判断")
        print()
    
    # 测试1: 今天的所有帖子筛选
    print(f"\n🎯 测试1: 筛选今天的所有帖子（使用真实时间进行逻辑）...")
    today_posts = downloader.filter_today_posts(test_posts)
    
    print(f"✅ 今天的帖子筛选结果:")
    print(f"   筛选出: {len(today_posts)}/{len(test_posts)} 个帖子")
    if today_posts:
        for i, post in enumerate(today_posts, 1):
            print(f"      {i}. {post.title}")
            print(f"         真实时间: {post.post_time}")
            print(f"         相对时间: {post.post_time_str}")
    else:
        print("   没有筛选出任何帖子")
    
    # 测试2: 最近24小时内的帖子筛选
    print(f"\n🎯 测试2: 筛选最近24小时内的帖子（使用真实时间进行逻辑）...")
    recent_24h_posts = downloader.filter_recent_hours_posts(test_posts, 24)
    
    print(f"✅ 最近24小时筛选结果:")
    print(f"   筛选出: {len(recent_24h_posts)}/{len(test_posts)} 个帖子")
    if recent_24h_posts:
        for i, post in enumerate(recent_24h_posts, 1):
            time_diff = now - post.post_time
            hours_diff = time_diff.total_seconds() / 3600
            print(f"      {i}. {post.title}")
            print(f"         真实时间: {post.post_time}")
            print(f"         相对时间: {post.post_time_str}")
            print(f"         时间差: {hours_diff:+.1f}小时")
    else:
        print("   没有筛选出任何帖子")
    
    print(f"\n💡 设计优势:")
    print(f"   ✅ 相对时间字符串仅用于展示，不参与逻辑计算")
    print(f"   ✅ 时间筛选逻辑完全基于真实时间，准确可靠")
    print(f"   ✅ 展示信息和逻辑处理分离，职责清晰")
    print(f"   ✅ 便于调试和日志记录")

if __name__ == "__main__":
    test_time_logic_separation()
