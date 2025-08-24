#!/usr/bin/env python3
"""
简单测试AI客户端基本功能
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_ai_client_basic():
    """测试AI客户端基本功能"""
    print("🔧 测试AI客户端基本功能...")
    
    try:
        from core.ai_client import AIClientManager, AIProvider
        from core.config import QQChannelConfig
        
        print("✅ 导入成功")
        
        # 创建配置
        config = QQChannelConfig()
        print("✅ 配置创建成功")
        
        # 测试OpenRouter客户端
        print("\n🔄 测试OpenRouter客户端...")
        try:
            ai_manager = AIClientManager(config, AIProvider.OPENROUTER)
            print("✅ OpenRouter客户端创建成功")
            
            # 测试获取可用客户端
            client = await ai_manager.get_available_client()
            print(f"✅ 获取到客户端: {type(client).__name__}")
            
        except Exception as e:
            print(f"❌ OpenRouter客户端测试失败: {e}")
        
        # 测试GitHub Models客户端
        print("\n🔄 测试GitHub Models客户端...")
        try:
            ai_manager = AIClientManager(config, AIProvider.GITHUB_MODELS)
            print("✅ GitHub Models客户端创建成功")
            
            # 测试获取可用客户端
            client = await ai_manager.get_available_client()
            print(f"✅ 获取到客户端: {type(client).__name__}")
            
        except Exception as e:
            print(f"❌ GitHub Models客户端测试失败: {e}")
        
        # 测试CherryStudio客户端
        print("\n🔄 测试CherryStudio客户端...")
        try:
            ai_manager = AIClientManager(config, AIProvider.CHERRYSTUDIO)
            print("✅ CherryStudio客户端创建成功")
            
            # 测试获取可用客户端
            client = await ai_manager.get_available_client()
            print(f"✅ 获取到客户端: {type(client).__name__}")
            
        except Exception as e:
            print(f"❌ CherryStudio客户端测试失败: {e}")
        
        # 测试Gemini客户端
        print("\n🔄 测试Gemini客户端...")
        try:
            ai_manager = AIClientManager(config, AIProvider.GEMINI)
            print("✅ Gemini客户端创建成功")
            
            # 测试获取可用客户端
            client = await ai_manager.get_available_client()
            print(f"✅ 获取到客户端: {type(client).__name__}")
            
        except Exception as e:
            print(f"❌ Gemini客户端测试失败: {e}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_image_processor():
    """测试图片处理器"""
    print("\n🖼️ 测试图片处理器...")
    
    try:
        from utils.image_processor import ImageProcessor
        print("✅ ImageProcessor导入成功")
        
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
                        
                        # 测试第一张图片
                        test_image = image_files[0]
                        print(f"\n🔍 测试图片: {test_image.name}")
                        
                        try:
                            # 测试图片处理
                            img_data, mime_type = ImageProcessor.process_image_for_ai(str(test_image))
                            print(f"✅ 图片处理成功")
                            print(f"  📊 数据大小: {len(img_data)} bytes")
                            print(f"  🏷️  MIME类型: {mime_type}")
                            
                        except Exception as e:
                            print(f"❌ 图片处理失败: {e}")
                    else:
                        print("❌ 没有找到图片文件")
                else:
                    print("❌ 图片目录不存在")
            else:
                print("❌ 没有找到帖子目录")
        else:
            print("❌ 数据目录不存在")
            
    except Exception as e:
        print(f"❌ 图片处理器测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    print("🚀 开始测试AI客户端基本功能")
    
    # 测试AI客户端基本功能
    await test_ai_client_basic()
    
    # 测试图片处理器
    await test_image_processor()
    
    print("\n✨ 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
