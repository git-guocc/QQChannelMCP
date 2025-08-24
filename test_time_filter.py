#!/usr/bin/env python3
"""
测试时间筛选功能 - 今天的所有帖子
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from complete_hellokitty_downloader import CompleteHelloKittyDownloader

def test_time_filter():
    """测试时间筛选功能"""
    print("🔍 测试时间筛选功能（今天的所有帖子）...")
    
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
    tomorrow_start = today_start + timedelta(days=1)
    
    test_posts = [
        MockPost("今天凌晨1点", today_start + timedelta(hours=1)),      # 今天1点
        MockPost("今天早上6点", today_start + timedelta(hours=6)),      # 今天6点
        MockPost("今天中午12点", today_start + timedelta(hours=12)),    # 今天12点
        MockPost("今天下午3点", today_start + timedelta(hours=15)),     # 今天15点
        MockPost("今天晚上11点", today_start + timedelta(hours=23)),    # 今天23点
        MockPost("昨天凌晨1点", today_start - timedelta(hours=23)),     # 昨天1点
        MockPost("昨天中午12点", today_start - timedelta(hours=12)),    # 昨天12点
        MockPost("昨天晚上11点", today_start - timedelta(hours=1)),     # 昨天23点
        MockPost("前天凌晨1点", today_start - timedelta(days=1, hours=23)), # 前天1点
        MockPost("明天凌晨1点", tomorrow_start + timedelta(hours=1)),   # 明天1点
    ]
    
    print(f"\n📅 当前时间: {now}")
    print(f"🌅 今天开始时间: {today_start}")
    print(f"🌙 明天开始时间: {tomorrow_start}")
    
    print(f"\n📝 测试帖子:")
    for i, post in enumerate(test_posts, 1):
        # 判断是否在今天
        is_today = today_start <= post.post_time < tomorrow_start
        status = "✅ 今天" if is_today else "❌ 不是今天"
        print(f"   {i}. {post.title} - 发帖时间: {post.post_time} - {status}")
    
    # 测试时间筛选
    print(f"\n🎯 开始时间筛选...")
    filtered_posts = downloader.filter_24h_posts(test_posts)
    
    print(f"\n✅ 筛选结果:")
    print(f"   总帖子数: {len(test_posts)}")
    print(f"   筛选后帖子数: {len(filtered_posts)}")
    
    if filtered_posts:
        print(f"   筛选出的帖子:")
        for i, post in enumerate(filtered_posts, 1):
            print(f"      {i}. {post.title} - 发帖时间: {post.post_time}")
    else:
        print("   没有筛选出任何帖子")
    
    # 验证筛选逻辑
    print(f"\n🔍 验证筛选逻辑:")
    for post in test_posts:
        downloader.current_post = post
        is_today = downloader._is_within_24h(None, now)
        
        expected = today_start <= post.post_time < tomorrow_start
        status = "✅ 正确" if is_today == expected else "❌ 错误"
        print(f"   {post.title}: {status} (期望: {expected}, 实际: {is_today})")
    
    # 显示时间范围
    print(f"\n⏰ 时间范围分析:")
    print(f"   今天范围: [{today_start}, {tomorrow_start})")
    print(f"   只有发帖时间在这个范围内的帖子才会被下载")
    print(f"   这意味着：")
    print(f"   - 今天0点、1点、12点、23点的帖子 ✅ 会被下载")
    print(f"   - 昨天任何时间的帖子 ❌ 不会被下载")
    print(f"   - 明天任何时间的帖子 ❌ 不会被下载")

if __name__ == "__main__":
    test_time_filter()
