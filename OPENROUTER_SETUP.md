# OpenRouter AI客户端配置指南

## 🎯 **OpenRouter简介**

OpenRouter是一个AI模型聚合平台，提供多种AI模型的统一API接口，包括：

- **GPT-4o系列** - OpenAI最新多模态模型
- **Claude 3.5系列** - Anthropic多模态模型  
- **Gemini系列** - Google多模态模型
- **多种开源模型** - Mistral、Llama等

## ✅ **图文功能支持**

OpenRouter完全支持我们的HelloKitty图片识别功能：

- **多模态输入**: 支持文本+图片输入
- **图片格式**: 支持JPEG、PNG、WebP等
- **模型选择**: 可选择最适合的模型
- **成本效益**: 比直接使用原厂API更便宜

## 🔧 **配置步骤**

### 1. 获取API密钥

1. 访问 [OpenRouter官网](https://openrouter.ai/)
2. 注册账号并登录
3. 在控制台获取API密钥

### 2. 更新环境变量

在`.env`文件中添加：

```bash
# OpenRouter配置
OPENROUTER_API_KEY=your_actual_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# 设置OpenRouter为优先提供商
AI_PREFERRED_PROVIDER=openrouter
```

### 3. 选择模型

OpenRouter支持多种模型，推荐用于图片分析：

```python
# 在代码中可以动态选择模型
models = [
    "openai/gpt-4o-mini",      # 性价比最高
    "openai/gpt-4o",           # 性能最好
    "anthropic/claude-3.5-sonnet", # 稳定可靠
    "google/gemini-pro-1.5"    # Google模型
]
```

## 🧪 **测试验证**

运行测试脚本验证配置：

```bash
python test_openrouter_client.py
```

## 💰 **成本分析**

### 免费额度
- 新用户通常有免费额度
- 可以测试功能

### 付费价格（示例）
- **GPT-4o-mini**: $0.00015/1K tokens (输入)
- **图片分析**: $0.000217/图片
- **比原厂便宜**: 通常有折扣

## 🚀 **优势特点**

1. **多模型支持**: 一个API访问多个AI模型
2. **成本优化**: 比直接使用原厂API便宜
3. **功能完整**: 完全支持图文分析
4. **稳定可靠**: 企业级服务
5. **易于集成**: 兼容OpenAI格式

## 🔄 **故障转移策略**

我们的系统现在支持多AI提供商：

1. **OpenRouter** (优先) - 支持图文，成本低
2. **GitHub Models** (备选) - 支持图文，免费
3. **Gemini** (备选) - 支持图文，有配额限制
4. **CherryStudio** (备选) - 仅文本

## 📝 **使用示例**

```python
from core.ai_client import AIClientManager, AIProvider

# 使用OpenRouter
ai_manager = AIClientManager(config, AIProvider.OPENROUTER)
client = await ai_manager.get_available_client()

# 图片分析
result = await client.analyze_image(image_path, prompt)
```

## 🎉 **总结**

OpenRouter是一个优秀的AI服务聚合平台，完全支持我们的图文功能需求，并且具有成本优势。建议将其作为主要的AI提供商，其他服务作为备选方案。
