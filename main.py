#!/usr/bin/env python3
"""
QQ频道数据采集工具主程序
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from core.config import QQChannelConfig
from collector.channel_scraper import QQChannelScraper
from collector.filter_engine import FilterEngine
from models.filter_criteria import FilterCriteria, QuickFilters
from storage.json_storage import JSONStorage
from storage.csv_storage import CSVStorage
from utils.url_parser import URLParser


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='QQ频道数据采集工具')
    parser.add_argument('command', choices=['collect', 'test', 'server'], 
                       help='执行的命令')
    parser.add_argument('--url', '-u', required=True, help='QQ频道URL')
    parser.add_argument('--max-posts', '-n', type=int, default=50, 
                       help='最大采集数量')
    parser.add_argument('--output', '-o', default='data/posts.json', 
                       help='输出文件路径')
    parser.add_argument('--format', '-f', choices=['json', 'csv'], default='json',
                       help='输出格式')
    parser.add_argument('--keywords', '-k', nargs='+', 
                       help='关键词筛选')
    parser.add_argument('--min-likes', type=int, 
                       help='最小点赞数')
    parser.add_argument('--days', type=int, 
                       help='最近几天的数据')
    parser.add_argument('--save-images', action='store_true', 
                       help='下载图片')
    
    args = parser.parse_args()
    
    # 初始化配置和组件
    config = QQChannelConfig()
    scraper = QQChannelScraper(config)
    filter_engine = FilterEngine()
    url_parser = URLParser()
    
    try:
        if args.command == 'test':
            # 测试连接
            print(f"测试连接: {args.url}")
            result = await scraper.test_connection(args.url)
            print(f"结果: {result}")
            
        elif args.command == 'collect':
            # 数据采集
            print(f"开始采集: {args.url}")
            
            # 验证URL
            if not url_parser.is_valid_qq_channel_url(args.url):
                print("错误: 不是有效的QQ频道URL")
                return
            
            # 采集数据
            posts = await scraper.scrape_channel_posts(args.url, args.max_posts)
            print(f"原始采集: {len(posts)} 个帖子")
            
            # 应用筛选条件
            if args.keywords or args.min_likes or args.days:
                criteria = FilterCriteria(
                    keywords=args.keywords or [],
                    min_likes=args.min_likes,
                    time_range_days=args.days
                )
                
                filtered_posts = await filter_engine.filter_posts(posts, criteria)
                print(f"筛选后: {len(filtered_posts)} 个帖子")
                posts = filtered_posts
            
            # 保存数据
            if args.format == 'csv':
                storage = CSVStorage(args.output)
                await storage.save_posts(posts)
            else:
                storage = JSONStorage(args.output)
                await storage.save_posts(posts)
            
            print(f"数据已保存到: {args.output}")
            
        elif args.command == 'server':
            # 启动MCP服务器
            print("启动MCP服务器...")
            from server.mcp_server import app
            app.run_stdio()
    
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
