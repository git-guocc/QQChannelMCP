#!/usr/bin/env python3
"""
测试AI客户端基本功能
"""

import sys
from pathlib import Path
import asyncio

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.ai_client import AIClientManager, AIProvider
from core.config import QQChannelConfig

async def test_ai_client_basic():
    """测试AI客户端基本功能"""
    print("🤖 测试AI客户端基本功能...")
    
    try:
        config = QQChannelConfig()
        
        # 测试GitHub Models
        print("\n🔧 测试GitHub Models...")
        try:
            ai_manager = AIClientManager(config, AIProvider.GITHUB_MODELS)
            client = await ai_manager.get_available_client()
            
            if client:
                print("✅ GitHub Models客户端可用")
                
                # 测试文本生成
                print("   测试文本生成...")
                response = await client.generate_text("Hello, 请回复'测试成功'")
                
                if response.success:
                    print(f"   ✅ 文本生成成功: {response.content}")
                else:
                    print(f"   ❌ 文本生成失败: {response.error}")
            else:
                print("❌ GitHub Models客户端不可用")
                
        except Exception as e:
            print(f"   ❌ GitHub Models测试异常: {e}")
        
        # 测试CherryStudio
        print("\n🔧 测试CherryStudio...")
        try:
            ai_manager = AIClientManager(config, AIProvider.CHERRYSTUDIO)
            client = await ai_manager.get_available_client()
            
            if client:
                print("✅ CherryStudio客户端可用")
                
                # 测试文本生成
                print("   测试文本生成...")
                response = await client.generate_text("Hello, 请回复'测试成功'")
                
                if response.success:
                    print(f"   ✅ 文本生成成功: {response.content}")
                else:
                    print(f"   ❌ 文本生成失败: {response.error}")
            else:
                print("❌ CherryStudio客户端不可用")
                
        except Exception as e:
            print(f"   ❌ CherryStudio测试异常: {e}")
        
        # 测试Gemini（可能有限制）
        print("\n🔧 测试Gemini...")
        try:
            ai_manager = AIClientManager(config, AIProvider.GEMINI)
            client = await ai_manager.get_available_client()
            
            if client:
                print("✅ Gemini客户端可用")
                
                # 测试文本生成
                print("   测试文本生成...")
                response = await client.generate_text("Hello, 请回复'测试成功'")
                
                if response.success:
                    print(f"   ✅ 文本生成成功: {response.content}")
                else:
                    print(f"   ❌ 文本生成失败: {response.error}")
            else:
                print("❌ Gemini客户端不可用")
                
        except Exception as e:
            print(f"   ❌ Gemini测试异常: {e}")
        
        print(f"\n💡 总结:")
        print(f"   📝 文本生成功能测试完成")
        print(f"   🖼️  图片分析功能需要Gemini（可能有配额限制）")
        print(f"   🔄 可以配置多个AI提供商作为备选")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_client_basic())
