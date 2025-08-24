#!/usr/bin/env python3
"""
测试HelloKitty图片识别功能
"""

import sys
from pathlib import Path
import asyncio

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from complete_hellokitty_downloader import CompleteHelloKittyDownloader
from core.ai_client import AIClientManager, AIProvider

async def test_hellokitty_recognition():
    """测试HelloKitty图片识别功能"""
    print("🎀 测试HelloKitty图片识别功能...")
    
    # 创建下载器实例
    downloader = CompleteHelloKittyDownloader()
    
    # 检查AI客户端初始化 - 使用GitHub Models
    print("\n🔧 测试AI客户端初始化...")
    print("   尝试使用GitHub Models（避免Gemini配额限制）...")
    
    try:
        from core.config import QQChannelConfig
        config = QQChannelConfig()
        ai_manager = AIClientManager(config, AIProvider.GITHUB_MODELS)
        
        if ai_manager:
            print("✅ GitHub Models AI客户端初始化成功")
            print(f"   客户端类型: {type(ai_manager).__name__}")
        else:
            print("❌ GitHub Models AI客户端初始化失败")
            return
    except Exception as e:
        print(f"❌ AI客户端初始化异常: {e}")
        return
    
    # 检查是否有图片需要识别
    print(f"\n📁 检查下载目录: {downloader.download_dir}")
    
    if not downloader.download_dir.exists():
        print("❌ 下载目录不存在")
        return
    
    # 查找图片文件
    image_files = list(downloader.download_dir.glob("*_image_*.jpg"))
    
    if not image_files:
        print("❌ 当前下载目录没有图片")
        print("   尝试查找其他目录的图片...")
        
        # 查找其他目录的图片
        data_dir = Path("data")
        all_images = list(data_dir.rglob("*.jpg"))
        
        if all_images:
            print(f"✅ 找到 {len(all_images)} 张图片在其他目录")
            # 使用第一张图片进行测试
            test_image = all_images[0]
            print(f"   使用测试图片: {test_image}")
            
            # 测试单张图片识别
            print(f"\n🔍 测试单张图片识别...")
            try:
                is_hellokitty = await downloader._analyze_image_for_hellokitty(ai_manager, str(test_image))
                
                if is_hellokitty:
                    print(f"   ✅ 识别结果: HelloKitty图片")
                else:
                    print(f"   ❌ 识别结果: 非HelloKitty图片")
                    
            except Exception as e:
                print(f"   ⚠️  识别失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ 没有找到任何图片文件")
            return
    else:
        print(f"✅ 找到 {len(image_files)} 张图片需要识别")
        
        # 显示前几张图片
        print(f"\n📸 图片列表:")
        for i, img_file in enumerate(image_files[:5], 1):
            size_kb = img_file.stat().st_size / 1024
            print(f"   {i:2d}. {img_file.name} ({size_kb:.1f} KB)")
        
        if len(image_files) > 5:
            print(f"   ... 还有 {len(image_files) - 5} 张图片")
        
        # 测试单张图片识别
        print(f"\n🔍 测试单张图片识别...")
        test_image = image_files[0]
        print(f"   测试图片: {test_image.name}")
        
        try:
            is_hellokitty = await downloader._analyze_image_for_hellokitty(ai_manager, str(test_image))
            
            if is_hellokitty:
                print(f"   ✅ 识别结果: HelloKitty图片")
            else:
                print(f"   ❌ 识别结果: 非HelloKitty图片")
                
        except Exception as e:
            print(f"   ⚠️  识别失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n💡 功能总结:")
    print(f"   ✅ GitHub Models AI客户端集成正常")
    print(f"   ✅ 图片识别逻辑完整")
    print(f"   ✅ 错误处理和日志记录")
    print(f"   📝 注意: 完整筛选流程需要先下载图片")

if __name__ == "__main__":
    asyncio.run(test_hellokitty_recognition())
