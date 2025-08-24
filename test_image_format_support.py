#!/usr/bin/env python3
"""
测试不同AI提供商对各种图片格式的支持
"""

import asyncio
import sys
import os
sys.path.append('src')

from core.ai_client import AIClientManager, AIProvider
from core.config import QQChannelConfig

async def test_image_format_support():
    """测试不同AI提供商对各种图片格式的支持"""
    print('🎯 测试不同AI提供商对各种图片格式的支持...')
    
    # 测试图片路径
    test_images = [
        'data/dayupdate/10_posts_2025-08-23/images/20250823_194605_image_01.jpg',  # AVIF格式
        'data/dayupdate/10_posts_2025-08-23/images/20250823_193130_image_01.jpg',  # AVIF格式
    ]
    
    # 检查图片是否存在
    available_images = []
    for img_path in test_images:
        if os.path.exists(img_path):
            available_images.append(img_path)
            # 检查实际格式
            import subprocess
            try:
                result = subprocess.run(['file', img_path], capture_output=True, text=True)
                print(f'📸 {img_path}: {result.stdout.strip()}')
            except:
                print(f'📸 {img_path}: 存在')
    
    if not available_images:
        print('❌ 没有找到可用的测试图片')
        return
    
    print(f'\n✅ 找到 {len(available_images)} 张测试图片')
    
    # 测试不同的AI提供商
    providers = [
        (AIProvider.OPENROUTER, "OpenRouter"),
        (AIProvider.GITHUB_MODELS, "GitHub Models"),
        (AIProvider.GEMINI, "Gemini")
    ]
    
    # 测试提示词
    prompt = '''
    请分析这张图片是否包含HelloKitty元素。
    
    HelloKitty特征：
    - 白色小猫形象
    - 通常戴着蝴蝶结
    - 可爱的卡通风格
    - 可能是HelloKitty品牌相关
    - 粉色、红色等HelloKitty常见颜色
    
    请只回答：是 或 否
    '''
    
    for provider_enum, provider_name in providers:
        print(f'\n🔍 测试 {provider_name}...')
        
        try:
            # 初始化AI客户端管理器
            config = QQChannelConfig()
            ai_manager = AIClientManager(config, provider_enum)
            
            # 获取可用的AI客户端
            ai_client = await ai_manager.get_available_client()
            if not ai_client:
                print(f'   ❌ {provider_name} 不可用')
                continue
            
            print(f'   ✅ {provider_name} 客户端获取成功')
            
            # 测试每张图片
            for img_path in available_images:
                print(f'   📸 测试图片: {os.path.basename(img_path)}')
                
                try:
                    result = await ai_client.analyze_image(img_path, prompt)
                    
                    if result.success:
                        is_hellokitty = '是' in result.content
                        print(f'      ✅ 分析成功: {result.content.strip()}')
                        print(f'         HelloKitty: {"是" if is_hellokitty else "否"}')
                        print(f'         置信度: {result.confidence}')
                        print(f'         提供商: {result.metadata.get("provider", "unknown")}')
                    else:
                        print(f'      ❌ 分析失败: {result.error}')
                        
                except Exception as e:
                    print(f'      ❌ 分析异常: {e}')
                    
        except Exception as e:
            print(f'   ❌ {provider_name} 测试失败: {e}')
    
    print(f'\n🎯 测试总结:')
    print(f'   这个测试帮助我们了解不同AI提供商对各种图片格式的支持情况')
    print(f'   以及我们的格式转换机制是否有效')

async def test_format_conversion():
    """测试图片格式转换功能"""
    print(f'\n🔧 测试图片格式转换功能...')
    
    # 测试图片路径
    test_image = 'data/dayupdate/10_posts_2025-08-23/images/20250823_194605_image_01.jpg'
    
    if not os.path.exists(test_image):
        print('❌ 测试图片不存在')
        return
    
    try:
        from PIL import Image
        import io
        
        # 检查原始格式
        with Image.open(test_image) as img:
            original_format = img.format
            original_mode = img.mode
            print(f'📸 原始图片格式: {original_format}, 模式: {original_mode}')
        
        # 测试格式转换
        with Image.open(test_image) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 转换为JPEG
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95)
            jpeg_data = img_byte_arr.getvalue()
            
            print(f'✅ 格式转换成功: {original_format} -> JPEG')
            print(f'   原始大小: {os.path.getsize(test_image)} bytes')
            print(f'   JPEG大小: {len(jpeg_data)} bytes')
            print(f'   压缩比: {len(jpeg_data) / os.path.getsize(test_image) * 100:.1f}%')
            
    except Exception as e:
        print(f'❌ 格式转换测试失败: {e}')

async def main():
    """主函数"""
    print("🚀 启动图片格式支持测试...")
    
    # 测试图片格式支持
    await test_image_format_support()
    
    # 测试格式转换功能
    await test_format_conversion()
    
    print(f'\n🎊 测试完成！')
    print(f'   这个测试帮助我们了解：')
    print(f'   1. 不同AI提供商支持哪些图片格式')
    print(f'   2. 我们的格式转换机制是否有效')
    print(f'   3. 是否需要为不同提供商优化图片处理')

if __name__ == '__main__':
    asyncio.run(main())
