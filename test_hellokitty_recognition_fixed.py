#!/usr/bin/env python3
"""
测试修复后的HelloKitty识别功能
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from complete_hellokitty_downloader import CompleteHelloKittyDownloader

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_hellokitty_recognition():
    """测试HelloKitty识别功能"""
    print("🎀 测试修复后的HelloKitty识别功能")
    
    try:
        # 创建下载器实例
        downloader = CompleteHelloKittyDownloader()
        
        # 测试AI客户端获取
        print("\n🔧 测试AI客户端获取...")
        ai_client = downloader._get_ai_client()
        
        if ai_client:
            print(f"✅ AI客户端获取成功: {type(ai_client).__name__}")
            
            # 测试图片识别
            print("\n🖼️ 测试图片识别...")
            
            # 查找测试图片
            test_images_dir = Path("data/dayupdate")
            if test_images_dir.exists():
                # 查找最新的图片目录
                image_dirs = [d for d in test_images_dir.iterdir() if d.is_dir() and "posts" in d.name]
                if image_dirs:
                    latest_dir = max(image_dirs, key=lambda x: x.stat().st_mtime)
                    images_dir = latest_dir / "images"
                    
                    if images_dir.exists():
                        image_files = list(images_dir.glob("*_image_*.jpg"))
                        if image_files:
                            print(f"📁 找到图片目录: {images_dir}")
                            print(f"📸 找到 {len(image_files)} 张图片")
                            
                            # 测试前3张图片
                            test_images = image_files[:3]
                            
                            for i, image_file in enumerate(test_images, 1):
                                print(f"\n🔍 测试图片 {i}: {image_file.name}")
                                
                                try:
                                    # 测试图片识别
                                    is_hellokitty = await downloader._analyze_image_for_hellokitty(
                                        ai_client, str(image_file)
                                    )
                                    
                                    print(f"  📊 识别结果: {'HelloKitty' if is_hellokitty else '非HelloKitty'}")
                                    
                                except Exception as e:
                                    print(f"  ❌ 识别失败: {e}")
                            
                            # 测试完整的筛选和复制流程
                            print(f"\n🔄 测试完整的筛选和复制流程...")
                            await downloader._filter_and_copy_hellokitty_images()
                            
                            # 检查HelloKitty文件夹
                            hellokitty_dir = images_dir.parent / "HelloKitty"
                            if hellokitty_dir.exists():
                                hellokitty_images = list(hellokitty_dir.glob("*.jpg"))
                                print(f"🎀 HelloKitty文件夹中有 {len(hellokitty_images)} 张图片")
                                
                                if hellokitty_images:
                                    print("  📸 HelloKitty图片列表:")
                                    for img in hellokitty_images:
                                        print(f"    - {img.name}")
                                else:
                                    print("  ⚠️  HelloKitty文件夹为空")
                            else:
                                print("  ❌ HelloKitty文件夹不存在")
                        else:
                            print("❌ 没有找到图片文件")
                    else:
                        print("❌ 图片目录不存在")
                else:
                    print("❌ 没有找到帖子目录")
            else:
                print("❌ 数据目录不存在")
        else:
            print("❌ AI客户端获取失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_ai_client_fallback():
    """测试AI客户端降级策略"""
    print("\n🔄 测试AI客户端降级策略...")
    
    try:
        from core.ai_client import AIClientManager, AIProvider
        from core.config import QQChannelConfig
        
        config = QQChannelConfig()
        
        # 测试不同的AI提供商
        providers = [
            ('openrouter', AIProvider.OPENROUTER),
            ('github_models', AIProvider.GITHUB_MODELS),
            ('cherrystudio', AIProvider.CHERRYSTUDIO),
            ('gemini', AIProvider.GEMINI)
        ]
        
        for provider_name, provider_enum in providers:
            print(f"\n🔧 测试 {provider_name}...")
            try:
                ai_manager = AIClientManager(config, provider_enum)
                print(f"  ✅ {provider_name} 初始化成功")
                
                # 测试获取可用客户端
                try:
                    client = await ai_manager.get_available_client()
                    print(f"  ✅ {provider_name} 客户端获取成功: {type(client).__name__}")
                except Exception as e:
                    print(f"  ❌ {provider_name} 客户端获取失败: {e}")
                    
            except Exception as e:
                print(f"  ❌ {provider_name} 初始化失败: {e}")
                
    except Exception as e:
        print(f"❌ 降级策略测试失败: {e}")


async def main():
    """主函数"""
    print("🚀 开始测试修复后的HelloKitty识别功能")
    
    # 测试AI客户端降级策略
    await test_ai_client_fallback()
    
    # 测试HelloKitty识别功能
    await test_hellokitty_recognition()
    
    print("\n✨ 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
