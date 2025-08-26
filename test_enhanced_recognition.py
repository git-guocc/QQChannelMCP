#!/usr/bin/env python3
"""
测试增强的HelloKitty识别服务
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.enhanced_hellokitty_recognition import EnhancedHelloKittyRecognitionService

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_enhanced_recognition():
    """测试增强的识别服务"""
    print("🎀 测试增强的HelloKitty识别服务")
    
    try:
        # 创建增强识别服务
        recognition_service = EnhancedHelloKittyRecognitionService()
        print("✅ 增强识别服务创建成功")
        
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
                        
                        # 测试前5张图片
                        test_images = image_files[:5]
                        
                        print(f"\n🔍 开始识别测试...")
                        for i, image_file in enumerate(test_images, 1):
                            print(f"\n--- 测试图片 {i}: {image_file.name} ---")
                            
                            try:
                                # 使用增强识别服务
                                result = await recognition_service.recognize_single_image(str(image_file))
                                
                                if result:
                                    print(f"  📊 识别结果: {'HelloKitty' if result.is_hellokitty else '非HelloKitty'}")
                                    print(f"  🎯 置信度: {result.confidence:.2f}")
                                    print(f"  🔍 识别方法: {result.recognition_method}")
                                    
                                    if result.ai_response:
                                        print(f"  🤖 AI响应: {result.ai_response}")
                                    
                                    if result.provider:
                                        print(f"  🌐 AI提供商: {result.provider}")
                                    
                                    if result.features:
                                        print(f"  🎨 特征信息: {result.features}")
                                    
                                    if result.needs_manual_review:
                                        print(f"  ⚠️  需要人工验证")
                                    
                                    print(f"  ⏱️  处理时间: {result.processing_time:.3f} 秒")
                                    print(f"  📏 文件大小: {result.file_size} bytes")
                                    print(f"  🏷️  原始格式: {result.original_format}")
                                else:
                                    print(f"  ❌ 识别失败")
                                    
                            except Exception as e:
                                print(f"  ❌ 识别异常: {e}")
                        
                        # 显示统计信息
                        print(f"\n📊 识别统计:")
                        recognition_service.print_statistics()
                        
                        # 测试批量识别
                        print(f"\n🔄 测试批量识别...")
                        all_results = []
                        for image_file in test_images:
                            result = await recognition_service.recognize_single_image(str(image_file))
                            if result:
                                all_results.append(result)
                        
                        # 分析结果
                        hellokitty_count = sum(1 for r in all_results if r.is_hellokitty)
                        print(f"  🎯 识别为HelloKitty: {hellokitty_count}/{len(all_results)}")
                        
                        # 按识别方法分组
                        method_stats = {}
                        for result in all_results:
                            method = result.recognition_method
                            if method not in method_stats:
                                method_stats[method] = 0
                            method_stats[method] += 1
                        
                        print(f"  🔍 识别方法分布:")
                        for method, count in method_stats.items():
                            print(f"    {method}: {count}")
                        
                    else:
                        print("❌ 没有找到图片文件")
                else:
                    print("❌ 图片目录不存在")
            else:
                print("❌ 没有找到帖子目录")
        else:
            print("❌ 数据目录不存在")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_recognition_strategies():
    """测试各种识别策略"""
    print("\n🔍 测试各种识别策略...")
    
    try:
        recognition_service = EnhancedHelloKittyRecognitionService()
        
        # 测试关键词识别
        print("\n🔑 测试关键词识别...")
        test_paths = [
            "test_hellokitty_image.jpg",
            "test_sanrio_cute.jpg",
            "test_pink_bow.jpg",
            "test_normal_image.jpg"
        ]
        
        for test_path in test_paths:
            result = recognition_service._keyword_based_recognition(test_path)
            print(f"  {test_path}: {'HelloKitty' if result else '非HelloKitty'}")
        
        # 测试保守策略
        print("\n🛡️ 测试保守策略...")
        test_paths = [
            "/path/to/hellokitty/channel/images/test.jpg",
            "/path/to/sanrio/folder/test.jpg",
            "/path/to/normal/folder/test.jpg"
        ]
        
        for test_path in test_paths:
            result = recognition_service._conservative_recognition(test_path)
            print(f"  {test_path}: {'HelloKitty' if result else '非HelloKitty'}")
            
    except Exception as e:
        print(f"❌ 策略测试失败: {e}")


async def main():
    """主函数"""
    print("🚀 开始测试增强的HelloKitty识别服务")
    
    # 测试增强识别服务
    await test_enhanced_recognition()
    
    # 测试识别策略
    await test_recognition_strategies()
    
    print("\n✨ 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
