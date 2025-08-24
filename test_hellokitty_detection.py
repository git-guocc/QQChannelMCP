#!/usr/bin/env python3
"""
测试HelloKitty图片检测功能
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_hellokitty_detection():
    """测试HelloKitty图片检测功能"""
    try:
        # 导入必要的模块
        from core.ai_client import AIClientManager, AIProvider
        from core.config import QQChannelConfig
        
        print("🔍 开始测试HelloKitty图片检测功能...")
        
        # 初始化配置
        config = QQChannelConfig()
        print(f"✅ 配置加载成功")
        print(f"   首选AI提供商: {config.ai_preferred_provider}")
        
        # 初始化AI客户端管理器
        ai_manager = AIClientManager(config, AIProvider.GEMINI)
        print(f"✅ AI客户端管理器初始化成功")
        
        # 测试AI连接
        print("\n🔗 测试AI服务连接...")
        try:
            # 测试Gemini连接
            gemini_client = ai_manager.gemini_client
            async with gemini_client as client:
                test_response = await client.generate_text("Hello, 请回复'连接成功'")
                if test_response.success:
                    print(f"✅ Gemini连接测试成功: {test_response.content}")
                else:
                    print(f"❌ Gemini连接测试失败: {test_response.error}")
        except Exception as e:
            print(f"❌ Gemini连接测试异常: {e}")
        
        # 获取图片目录
        images_dir = Path("data/dayupdate/10_posts_2025-08-23/images")
        if not images_dir.exists():
            print(f"❌ 图片目录不存在: {images_dir}")
            return
        
        # 获取所有图片文件
        image_files = [f for f in images_dir.glob("*.jpg") if f.is_file()]
        print(f"\n📁 找到 {len(image_files)} 张图片需要检测")
        
        # 创建HelloKitty文件夹
        hellokitty_dir = images_dir.parent / "HelloKitty"
        hellokitty_dir.mkdir(exist_ok=True)
        print(f"📂 HelloKitty文件夹: {hellokitty_dir}")
        
        # 测试图片检测
        print("\n🎀 开始检测HelloKitty图片...")
        hellokitty_count = 0
        
        for i, image_file in enumerate(image_files, 1):
            try:
                print(f"\n[{i:2d}/{len(image_files)}] 检测图片: {image_file.name}")
                
                # 使用AI分析图片
                is_hellokitty = await analyze_image_for_hellokitty(ai_manager, str(image_file))
                
                if is_hellokitty:
                    # 复制到HelloKitty文件夹
                    dest_file = hellokitty_dir / image_file.name
                    import shutil
                    shutil.copy2(image_file, dest_file)
                    hellokitty_count += 1
                    print(f"   ✅ 检测为HelloKitty图片，已复制到HelloKitty文件夹")
                else:
                    print(f"   ❌ 非HelloKitty图片")
                    
            except Exception as e:
                print(f"   ⚠️  检测失败: {e}")
                continue
        
        print(f"\n🎉 检测完成！")
        print(f"   总图片数: {len(image_files)}")
        print(f"   HelloKitty图片数: {hellokitty_count}")
        print(f"   HelloKitty文件夹: {hellokitty_dir}")
        
        # 显示HelloKitty文件夹中的图片
        if hellokitty_dir.exists():
            hellokitty_images = list(hellokitty_dir.glob("*.jpg"))
            if hellokitty_images:
                print(f"\n📸 HelloKitty文件夹中的图片:")
                for i, img in enumerate(hellokitty_images, 1):
                    size_kb = img.stat().st_size / 1024
                    print(f"   {i:2d}. {img.name} ({size_kb:.1f} KB)")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

async def analyze_image_for_hellokitty(ai_manager, image_path: str) -> bool:
    """分析图片是否包含HelloKitty元素"""
    try:
        # 获取AI客户端
        ai_client = await ai_manager.get_available_client()
        
        prompt = """
        请分析这张图片是否包含HelloKitty元素。
        
        HelloKitty特征：
        - 白色小猫形象
        - 通常戴着蝴蝶结
        - 可爱的卡通风格
        - 可能是HelloKitty品牌相关
        - 粉色、红色等HelloKitty常见颜色
        
        请只回答：是 或 否
        """
        
        result = await ai_client.analyze_image(image_path, prompt)
        
        if result.success:
            is_hellokitty = "是" in result.content
            print(f"      AI分析结果: {result.content.strip()}")
            return is_hellokitty
        else:
            print(f"      AI分析失败: {result.error}")
            return False
            
    except Exception as e:
        print(f"      AI分析异常: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_hellokitty_detection())
