#!/usr/bin/env python3
"""
测试OpenRouter AI客户端
"""

import asyncio
import sys
import os
sys.path.append('src')

from core.ai_client import AIClientManager, AIProvider
from core.config import QQChannelConfig

async def test_openrouter_client():
    """测试OpenRouter客户端"""
    print('🎯 测试OpenRouter AI客户端...')
    
    # 检查环境变量
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print('❌ 未设置OPENROUTER_API_KEY环境变量')
        print('💡 请在.env文件中添加: OPENROUTER_API_KEY=your_api_key_here')
        return False
    
    print(f'✅ 找到OpenRouter API密钥')
    
    # 初始化配置和AI客户端管理器
    config = QQChannelConfig()
    ai_manager = AIClientManager(config, AIProvider.OPENROUTER)
    
    print(f'✅ AI客户端管理器初始化成功')
    
    # 获取OpenRouter客户端
    try:
        openrouter_client = ai_manager.openrouter_client
        print(f'✅ OpenRouter客户端获取成功: {type(openrouter_client).__name__}')
    except Exception as e:
        print(f'❌ 获取OpenRouter客户端失败: {e}')
        return False
    
    # 测试连接
    print(f'🔍 测试OpenRouter连接...')
    try:
        async with openrouter_client as client:
            if await client.test_connection():
                print(f'🎉 OpenRouter连接测试成功！')
            else:
                print(f'❌ OpenRouter连接测试失败')
                return False
    except Exception as e:
        print(f'❌ OpenRouter连接测试异常: {e}')
        return False
    
    # 测试文本生成
    print(f'🔍 测试文本生成...')
    try:
        response = await openrouter_client.generate_text("请简单介绍一下OpenRouter")
        if response.success:
            print(f'✅ 文本生成成功: {response.content[:100]}...')
        else:
            print(f'❌ 文本生成失败: {response.error}')
            return False
    except Exception as e:
        print(f'❌ 文本生成异常: {e}')
        return False
    
    # 测试图片分析（如果有图片的话）
    image_path = 'data/dayupdate/10_posts_2025-08-23/images/20250823_194605_image_01.jpg'
    if os.path.exists(image_path):
        print(f'🔍 测试图片分析功能...')
        try:
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
            
            result = await openrouter_client.analyze_image(image_path, prompt)
            if result.success:
                print(f'🎉 图片分析成功!')
                print(f'   AI响应: {result.content.strip()}')
                print(f'   置信度: {result.confidence}')
                print(f'   提供商: {result.metadata.get("provider", "unknown")}')
            else:
                print(f'❌ 图片分析失败: {result.error}')
                return False
        except Exception as e:
            print(f'❌ 图片分析异常: {e}')
            return False
    else:
        print(f'⚠️ 跳过图片分析测试（测试图片不存在）')
    
    print(f'\n🎊 OpenRouter客户端测试完成！')
    return True

async def test_all_providers():
    """测试所有AI提供商"""
    print('\n🔍 测试所有AI提供商状态...')
    
    config = QQChannelConfig()
    ai_manager = AIClientManager(config)
    
    # 获取提供商状态
    status = ai_manager.get_provider_status()
    print(f'📊 提供商配置状态:')
    for provider, info in status.items():
        config_status = "✅ 已配置" if info["configured"] else "❌ 未配置"
        print(f'   {provider}: {config_status}')
    
    # 测试所有客户端
    print(f'\n🧪 测试所有客户端连接...')
    try:
        results = await ai_manager.test_all_clients()
        for provider, result in results.items():
            status_icon = "✅" if result else "❌"
            print(f'   {provider}: {status_icon} {"可用" if result else "不可用"}')
    except Exception as e:
        print(f'❌ 测试客户端失败: {e}')

async def main():
    """主函数"""
    print("🚀 启动OpenRouter客户端测试...")
    
    # 测试OpenRouter客户端
    success = await test_openrouter_client()
    
    if success:
        # 测试所有提供商
        await test_all_providers()
        
        print(f'\n🎯 测试总结:')
        print(f'   ✅ OpenRouter客户端集成成功')
        print(f'   ✅ 支持文本生成')
        print(f'   ✅ 支持图片分析')
        print(f'   💡 可以作为Gemini的替代方案')
    else:
        print(f'\n❌ OpenRouter客户端测试失败')
        print(f'   💡 请检查API密钥配置')

if __name__ == '__main__':
    asyncio.run(main())
