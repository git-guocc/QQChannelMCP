"""
AI客户端模块 - 支持多个AI提供商 (Gemini, GitHub Copilot)
"""

import asyncio
import logging
import aiohttp
import json
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum

from .config import QQChannelConfig
from .exceptions import QQChannelMCPError

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """AI提供商枚举"""
    GEMINI = "gemini"
    GITHUB_MODELS = "github_models"
    CHERRYSTUDIO = "cherrystudio"
    OPENROUTER = "openrouter"


@dataclass
class AIResponse:
    """AI响应结果"""
    success: bool
    content: str
    error: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class GeminiClient:
    """Gemini AI客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://generativelanguage.googleapis.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # API配置
        self.model = "gemini-1.5-pro"  # 支持图像识别的模型
        self.max_tokens = 2048
        self.temperature = 0.7
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "Content-Type": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        """
        生成文本响应
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            
        Returns:
            AI响应结果
        """
        try:
            if not self.session:
                async with self:
                    return await self._generate_text_internal(prompt, system_prompt)
            else:
                return await self._generate_text_internal(prompt, system_prompt)
                
        except Exception as e:
            logger.error(f"Gemini API调用失败: {e}")
            return AIResponse(
                success=False,
                content="",
                error=str(e)
            )
    
    async def analyze_image(self, image_path: str, prompt: str) -> AIResponse:
        """使用Gemini Vision API分析图片"""
        try:
            import base64
            
            # 读取图片文件
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 构建包含图像的请求
            request_data = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": base64.b64encode(image_data).decode('utf-8')
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": self.max_tokens
                }
            }
            
            # 调用API
            url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            
            async with self.session.post(url, json=request_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise QQChannelMCPError(f"Gemini Vision API错误 {response.status}: {error_text}")
                
                result = await response.json()
                
                # 解析响应
                try:
                    content = result["candidates"][0]["content"]["parts"][0]["text"]
                    
                    return AIResponse(
                        success=True,
                        content=content.strip(),
                        confidence=0.8,
                        metadata={
                            "model": self.model,
                            "finish_reason": result["candidates"][0].get("finishReason", "STOP")
                        }
                    )
                    
                except (KeyError, IndexError) as e:
                    raise QQChannelMCPError(f"解析Gemini Vision响应失败: {e}, 响应: {result}")
                    
        except Exception as e:
            logger.error(f"Gemini Vision API调用失败: {e}")
            return AIResponse(
                success=False,
                content="",
                error=str(e)
            )
    
    async def _generate_text_internal(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        """内部文本生成方法"""
        
        # 构建消息内容
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Gemini API请求体
        request_data = {
            "contents": [
                {
                    "parts": [
                        {"text": full_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
                "topP": 0.8,
                "topK": 10
            }
        }
        
        # API URL
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        async with self.session.post(url, json=request_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise QQChannelMCPError(f"Gemini API错误 {response.status}: {error_text}")
            
            result = await response.json()
            
            # 解析响应
            try:
                content = result["candidates"][0]["content"]["parts"][0]["text"]
                
                # 获取安全评分作为置信度参考
                safety_ratings = result["candidates"][0].get("safetyRatings", [])
                confidence = 0.8  # 默认置信度
                
                return AIResponse(
                    success=True,
                    content=content.strip(),
                    confidence=confidence,
                    metadata={
                        "model": self.model,
                        "safety_ratings": safety_ratings,
                        "finish_reason": result["candidates"][0].get("finishReason", "STOP")
                    }
                )
                
            except (KeyError, IndexError) as e:
                raise QQChannelMCPError(f"解析Gemini响应失败: {e}, 响应: {result}")
    
    async def filter_content(self, content: str, filter_prompt: str) -> AIResponse:
        """
        使用AI筛选内容
        
        Args:
            content: 要筛选的内容
            filter_prompt: 筛选条件描述
            
        Returns:
            筛选结果
        """
        system_prompt = """你是一个内容筛选助手。请根据给定的筛选条件判断内容是否符合要求。

请只回答 "是" 或 "否"，不要添加其他解释。

筛选条件: {filter_prompt}

要判断的内容: {content}

你的判断:"""
        
        prompt = system_prompt.format(
            filter_prompt=filter_prompt,
            content=content[:1000]  # 限制内容长度
        )
        
        return await self.generate_text(prompt)
    
    async def analyze_content(self, content: str, analysis_type: str = "sentiment") -> AIResponse:
        """
        分析内容
        
        Args:
            content: 要分析的内容
            analysis_type: 分析类型 (sentiment/topic/summary等)
            
        Returns:
            分析结果
        """
        
        if analysis_type == "sentiment":
            prompt = f"请分析以下内容的情感倾向，回答：积极、消极、中性\n\n内容：{content[:500]}"
        elif analysis_type == "topic":
            prompt = f"请提取以下内容的主要话题关键词（最多5个），用逗号分隔\n\n内容：{content[:500]}"
        elif analysis_type == "summary":
            prompt = f"请用一句话总结以下内容\n\n内容：{content[:800]}"
        else:
            prompt = f"请分析以下内容：{content[:500]}"
        
        return await self.generate_text(prompt)
    
    async def test_connection(self) -> bool:
        """测试API连接"""
        try:
            response = await self.generate_text("Hello, 请回复'连接成功'")
            return response.success and "连接成功" in response.content
        except Exception as e:
            logger.error(f"API连接测试失败: {e}")
            return False


class GitHubModelsClient:
    """GitHub Models AI客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://models.github.ai"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # API配置
        self.model = "gpt-4o"  # GitHub Models服务支持的模型
        self.max_tokens = 2048
        self.temperature = 0.7
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "QQChannelMCP/1.0"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        """
        生成文本响应
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            
        Returns:
            AI响应结果
        """
        try:
            if not self.session:
                async with self:
                    return await self._generate_text_internal(prompt, system_prompt)
            else:
                return await self._generate_text_internal(prompt, system_prompt)
                
        except Exception as e:
            logger.error(f"GitHub Models API调用失败: {e}")
            return AIResponse(
                success=False,
                content="",
                error=str(e)
            )
    
    async def _generate_text_internal(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        """内部文本生成方法"""
        
        # 构建消息数组 (OpenAI格式)
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user", 
            "content": prompt
        })
        
        # GitHub Copilot API请求体 (类似OpenAI格式)
        request_data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": 0.9,
            "stream": False
        }
        
        # GitHub AI模型推理服务API URL
        url = f"{self.base_url}/inference/v1/chat/completions"
        
        async with self.session.post(url, json=request_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise QQChannelMCPError(f"GitHub Models API错误 {response.status}: {error_text}")
            
            # GitHub Models API返回text/plain但内容是JSON
            response_text = await response.text()
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise QQChannelMCPError(f"GitHub Models API返回非JSON格式: {response_text[:200]}")
            
            # 解析响应 (OpenAI格式)
            try:
                content = result["choices"][0]["message"]["content"]
                finish_reason = result["choices"][0]["finish_reason"]
                
                # 计算置信度 (基于finish_reason)
                confidence = 0.9 if finish_reason == "stop" else 0.7
                
                return AIResponse(
                    success=True,
                    content=content.strip(),
                    confidence=confidence,
                    metadata={
                        "model": self.model,
                        "finish_reason": finish_reason,
                        "usage": result.get("usage", {}),
                        "provider": "github_models"
                    }
                )
                
            except (KeyError, IndexError) as e:
                raise QQChannelMCPError(f"解析GitHub Models响应失败: {e}, 响应: {result}")
    
    async def analyze_image(self, image_path: str, prompt: str) -> AIResponse:
        """使用GitHub Models分析图片"""
        try:
            import base64
            from utils.image_processor import ImageProcessor
            
            # 使用ImageProcessor处理图片格式
            img_byte_arr, mime_type = ImageProcessor.process_image_for_ai(image_path)
            
            # 构建包含图像的请求 (OpenAI格式)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64.b64encode(img_byte_arr).decode('utf-8')}"
                            }
                        }
                    ]
                }
            ]
            
            request_data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": 0.9,
                "stream": False
            }
            
            # GitHub AI模型推理服务API URL
            url = f"{self.base_url}/inference/v1/chat/completions"
            
            # 确保session可用
            if not self.session or self.session.closed:
                async with self:
                    return await self._analyze_image_internal(request_data)
            else:
                return await self._analyze_image_internal(request_data)
                    
        except Exception as e:
            logger.error(f"GitHub Models图片分析失败: {e}")
            return AIResponse(
                success=False,
                content="",
                error=str(e)
            )
    
    async def _analyze_image_internal(self, request_data: dict) -> AIResponse:
        """内部图片分析方法"""
        try:
            async with self.session.post(f"{self.base_url}/inference/v1/chat/completions", json=request_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise QQChannelMCPError(f"GitHub Models API错误 {response.status}: {error_text}")
                
                response_text = await response.text()
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError as e:
                    raise QQChannelMCPError(f"GitHub Models API返回非JSON格式: {response_text[:200]}")
                
                # 解析响应 (OpenAI格式)
                try:
                    content = result["choices"][0]["message"]["content"]
                    finish_reason = result["choices"][0]["finish_reason"]
                    
                    # 计算置信度 (基于finish_reason)
                    confidence = 0.9 if finish_reason == "stop" else 0.7
                    
                    return AIResponse(
                        success=True,
                        content=content.strip(),
                        confidence=confidence,
                        metadata={
                            "model": self.model,
                            "finish_reason": finish_reason,
                            "usage": result.get("usage", {}),
                            "provider": "github_models"
                        }
                    )
                    
                except (KeyError, IndexError) as e:
                    raise QQChannelMCPError(f"解析GitHub Models响应失败: {e}, 响应: {result}")
                    
        except Exception as e:
            logger.error(f"GitHub Models内部图片分析失败: {e}")
            return AIResponse(
                success=False,
                content="",
                error=str(e)
            )
    
    async def filter_content(self, content: str, filter_prompt: str) -> AIResponse:
        """
        使用AI筛选内容
        
        Args:
            content: 要筛选的内容
            filter_prompt: 筛选条件描述
            
        Returns:
            筛选结果
        """
        system_prompt = """你是一个内容筛选助手。请根据给定的筛选条件判断内容是否符合要求。

请只回答 "是" 或 "否"，不要添加其他解释。"""

        user_prompt = f"""筛选条件: {filter_prompt}

要判断的内容: {content[:1000]}

你的判断:"""
        
        return await self.generate_text(user_prompt, system_prompt)
    
    async def analyze_content(self, content: str, analysis_type: str = "sentiment") -> AIResponse:
        """
        分析内容
        
        Args:
            content: 要分析的内容
            analysis_type: 分析类型 (sentiment/topic/summary等)
            
        Returns:
            分析结果
        """
        
        if analysis_type == "sentiment":
            prompt = f"请分析以下内容的情感倾向，回答：积极、消极、中性\n\n内容：{content[:500]}"
        elif analysis_type == "topic":
            prompt = f"请提取以下内容的主要话题关键词（最多5个），用逗号分隔\n\n内容：{content[:500]}"
        elif analysis_type == "summary":
            prompt = f"请用一句话总结以下内容\n\n内容：{content[:800]}"
        else:
            prompt = f"请分析以下内容：{content[:500]}"
        
        return await self.generate_text(prompt)
    
    async def test_connection(self) -> bool:
        """测试API连接"""
        try:
            response = await self.generate_text("Hello, 请回复'连接成功'")
            return response.success and "连接成功" in response.content
        except Exception as e:
            logger.error(f"GitHub Copilot API连接测试失败: {e}")
            return False


class CherryStudioClient:
    """CherryStudio AI客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.cherrystudio.ai"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # API配置
        self.model = "gpt-4o" # CherryStudio支持的模型
        self.max_tokens = 2048
        self.temperature = 0.7
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "QQChannelMCP/1.0"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        """
        生成文本响应
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            
        Returns:
            AI响应结果
        """
        try:
            if not self.session:
                async with self:
                    return await self._generate_text_internal(prompt, system_prompt)
            else:
                return await self._generate_text_internal(prompt, system_prompt)
                
        except Exception as e:
            logger.error(f"CherryStudio API调用失败: {e}")
            return AIResponse(
                success=False,
                content="",
                error=str(e)
            )
    
    async def _generate_text_internal(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        """内部文本生成方法"""
        
        # 构建消息数组 (OpenAI格式)
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user", 
            "content": prompt
        })
        
        # CherryStudio API请求体 (类似OpenAI格式)
        request_data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": 0.9,
            "stream": False
        }
        
        # CherryStudio API URL
        url = f"{self.base_url}/v1/chat/completions"
        
        async with self.session.post(url, json=request_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise QQChannelMCPError(f"CherryStudio API错误 {response.status}: {error_text}")
            
            # CherryStudio API返回text/plain但内容是JSON
            response_text = await response.text()
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise QQChannelMCPError(f"CherryStudio API返回非JSON格式: {response_text[:200]}")
            
            # 解析响应 (OpenAI格式)
            try:
                content = result["choices"][0]["message"]["content"]
                finish_reason = result["choices"][0]["finish_reason"]
                
                # 计算置信度 (基于finish_reason)
                confidence = 0.9 if finish_reason == "stop" else 0.7
                
                return AIResponse(
                    success=True,
                    content=content.strip(),
                    confidence=confidence,
                    metadata={
                        "model": self.model,
                        "finish_reason": finish_reason,
                        "usage": result.get("usage", {}),
                        "provider": "cherrystudio"
                    }
                )
                
            except (KeyError, IndexError) as e:
                raise QQChannelMCPError(f"解析CherryStudio响应失败: {e}, 响应: {result}")
    
    async def filter_content(self, content: str, filter_prompt: str) -> AIResponse:
        """
        使用AI筛选内容
        
        Args:
            content: 要筛选的内容
            filter_prompt: 筛选条件描述
            
        Returns:
            筛选结果
        """
        system_prompt = """你是一个内容筛选助手。请根据给定的筛选条件判断内容是否符合要求。

请只回答 "是" 或 "否"，不要添加其他解释。"""

        user_prompt = f"""筛选条件: {filter_prompt}

要判断的内容: {content[:1000]}

你的判断:"""
        
        return await self.generate_text(user_prompt, system_prompt)
    
    async def analyze_content(self, content: str, analysis_type: str = "sentiment") -> AIResponse:
        """
        分析内容
        
        Args:
            content: 要分析的内容
            analysis_type: 分析类型 (sentiment/topic/summary等)
            
        Returns:
            分析结果
        """
        
        if analysis_type == "sentiment":
            prompt = f"请分析以下内容的情感倾向，回答：积极、消极、中性\n\n内容：{content[:500]}"
        elif analysis_type == "topic":
            prompt = f"请提取以下内容的主要话题关键词（最多5个），用逗号分隔\n\n内容：{content[:500]}"
        elif analysis_type == "summary":
            prompt = f"请用一句话总结以下内容\n\n内容：{content[:800]}"
        else:
            prompt = f"请分析以下内容：{content[:500]}"
        
        return await self.generate_text(prompt)
    
    async def test_connection(self) -> bool:
        """测试API连接"""
        try:
            response = await self.generate_text("Hello, 请回复'连接成功'")
            return response.success and "连接成功" in response.content
        except Exception as e:
            logger.error(f"CherryStudio API连接测试失败: {e}")
            return False


class OpenRouterClient:
    """OpenRouter AI客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # API配置
        self.model = "openai/gpt-4o" # OpenRouter支持的模型
        self.max_tokens = 2048
        self.temperature = 0.7
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "QQChannelMCP/1.0"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        """
        生成文本响应
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            
        Returns:
            AI响应结果
        """
        try:
            # 确保session可用
            if not self.session or self.session.closed:
                async with self:
                    return await self._generate_text_internal(prompt, system_prompt)
            else:
                return await self._generate_text_internal(prompt, system_prompt)
                
        except Exception as e:
            logger.error(f"OpenRouter API调用失败: {e}")
            return AIResponse(
                success=False,
                content="",
                error=str(e)
            )
    
    async def _generate_text_internal(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        """内部文本生成方法"""
        
        # 构建消息数组 (OpenAI格式)
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user", 
            "content": prompt
        })
        
        # OpenRouter API请求体 (类似OpenAI格式)
        request_data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": 0.9,
            "stream": False
        }
        
        # OpenRouter API URL
        url = f"{self.base_url}/chat/completions"
        
        async with self.session.post(url, json=request_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise QQChannelMCPError(f"OpenRouter API错误 {response.status}: {error_text}")
            
            # OpenRouter API返回text/plain但内容是JSON
            response_text = await response.text()
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise QQChannelMCPError(f"OpenRouter API返回非JSON格式: {response_text[:200]}")
            
            # 解析响应 (OpenAI格式)
            try:
                content = result["choices"][0]["message"]["content"]
                finish_reason = result["choices"][0]["finish_reason"]
                
                # 计算置信度 (基于finish_reason)
                confidence = 0.9 if finish_reason == "stop" else 0.7
                
                return AIResponse(
                    success=True,
                    content=content.strip(),
                    confidence=confidence,
                    metadata={
                        "model": self.model,
                        "finish_reason": finish_reason,
                        "usage": result.get("usage", {}),
                        "provider": "openrouter"
                    }
                )
                
            except (KeyError, IndexError) as e:
                raise QQChannelMCPError(f"解析OpenRouter响应失败: {e}, 响应: {result}")
    
    async def filter_content(self, content: str, filter_prompt: str) -> AIResponse:
        """
        使用AI筛选内容
        
        Args:
            content: 要筛选的内容
            filter_prompt: 筛选条件描述
            
        Returns:
            筛选结果
        """
        system_prompt = """你是一个内容筛选助手。请根据给定的筛选条件判断内容是否符合要求。

请只回答 "是" 或 "否"，不要添加其他解释。"""

        user_prompt = f"""筛选条件: {filter_prompt}

要判断的内容: {content[:1000]}

你的判断:"""
        
        return await self.generate_text(user_prompt, system_prompt)
    
    async def analyze_content(self, content: str, analysis_type: str = "sentiment") -> AIResponse:
        """
        分析内容
        
        Args:
            content: 要分析的内容
            analysis_type: 分析类型 (sentiment/topic/summary等)
            
        Returns:
            分析结果
        """
        
        if analysis_type == "sentiment":
            prompt = f"请分析以下内容的情感倾向，回答：积极、消极、中性\n\n内容：{content[:500]}"
        elif analysis_type == "topic":
            prompt = f"请提取以下内容的主要话题关键词（最多5个），用逗号分隔\n\n内容：{content[:500]}"
        elif analysis_type == "summary":
            prompt = f"请用一句话总结以下内容\n\n内容：{content[:800]}"
        else:
            prompt = f"请分析以下内容：{content[:500]}"
        
        return await self.generate_text(prompt)
    
    async def test_connection(self) -> bool:
        """测试API连接"""
        try:
            response = await self.generate_text("Hello, 请回复'连接成功'")
            return response.success and "连接成功" in response.content
        except Exception as e:
            logger.error(f"OpenRouter API连接测试失败: {e}")
            return False
    
    async def analyze_image(self, image_path: str, prompt: str) -> AIResponse:
        """使用OpenRouter分析图片"""
        try:
            import base64
            from utils.image_processor import ImageProcessor
            
            # 使用ImageProcessor处理图片格式
            img_byte_arr, mime_type = ImageProcessor.process_image_for_ai(image_path)
            
            # 构建包含图像的请求 (OpenAI格式)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64.b64encode(img_byte_arr).decode('utf-8')}"
                            }
                        }
                    ]
                }
            ]
            
            request_data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": 0.9,
                "stream": False
            }
            
            # 确保session可用
            if not self.session or self.session.closed:
                async with self:
                    return await self._analyze_image_internal(request_data)
            else:
                return await self._analyze_image_internal(request_data)
                
        except Exception as e:
            logger.error(f"OpenRouter图片分析失败: {e}")
            return AIResponse(
                success=False,
                content="",
                error=str(e)
            )
    

    
    async def _analyze_image_internal(self, request_data: dict) -> AIResponse:
        """内部图片分析方法"""
        try:
            async with self.session.post(f"{self.base_url}/chat/completions", json=request_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise QQChannelMCPError(f"OpenRouter API错误 {response.status}: {error_text}")
                
                response_text = await response.text()
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError as e:
                    raise QQChannelMCPError(f"OpenRouter API返回非JSON格式: {response_text[:200]}")
                
                # 解析响应 (OpenAI格式)
                try:
                    content = result["choices"][0]["message"]["content"]
                    finish_reason = result["choices"][0]["finish_reason"]
                    
                    # 计算置信度 (基于finish_reason)
                    confidence = 0.9 if finish_reason == "stop" else 0.7
                    
                    return AIResponse(
                        success=True,
                        content=content.strip(),
                        confidence=confidence,
                        metadata={
                            "model": self.model,
                            "finish_reason": finish_reason,
                            "usage": result.get("usage", {}),
                            "provider": "openrouter"
                        }
                    )
                    
                except (KeyError, IndexError) as e:
                    raise QQChannelMCPError(f"解析OpenRouter响应失败: {e}, 响应: {result}")
                    
        except Exception as e:
            logger.error(f"OpenRouter内部图片分析失败: {e}")
            return AIResponse(
                success=False,
                content="",
                error=str(e)
            )


class AIClientManager:
    """AI客户端管理器 - 支持多个AI提供商"""
    
    def __init__(self, config: QQChannelConfig, preferred_provider: AIProvider = AIProvider.GITHUB_MODELS):
        self.config = config
        self.preferred_provider = preferred_provider
        self._gemini_client: Optional[GeminiClient] = None
        self._models_client: Optional[GitHubModelsClient] = None
        self._cherrystudio_client: Optional[CherryStudioClient] = None
        self._openrouter_client: Optional[OpenRouterClient] = None
    
    @property
    def gemini_client(self) -> GeminiClient:
        """获取Gemini客户端"""
        if self._gemini_client is None:
            import os
            api_key = os.getenv("GEMINI_API_KEY")
            base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")
            
            if not api_key:
                raise QQChannelMCPError("未配置GEMINI_API_KEY环境变量")
            
            self._gemini_client = GeminiClient(api_key, base_url)
        
        return self._gemini_client
    
    @property
    def models_client(self) -> GitHubModelsClient:
        """获取GitHub Models客户端"""
        if self._models_client is None:
            import os
            api_key = os.getenv("GITHUB_MODELS_API_KEY")
            base_url = os.getenv("GITHUB_MODELS_BASE_URL", "https://models.github.ai")
            
            if not api_key:
                raise QQChannelMCPError("未配置GITHUB_MODELS_API_KEY环境变量")
            
            self._models_client = GitHubModelsClient(api_key, base_url)
        
        return self._models_client

    @property
    def cherrystudio_client(self) -> CherryStudioClient:
        """获取CherryStudio客户端"""
        if self._cherrystudio_client is None:
            import os
            api_key = os.getenv("CHERRYSTUDIO_API_KEY")
            base_url = os.getenv("CHERRYSTUDIO_BASE_URL", "https://api.cherrystudio.ai")
            
            if not api_key:
                raise QQChannelMCPError("未配置CHERRYSTUDIO_API_KEY环境变量")
            
            self._cherrystudio_client = CherryStudioClient(api_key, base_url)
        
        return self._cherrystudio_client

    @property
    def openrouter_client(self) -> OpenRouterClient:
        """获取OpenRouter客户端"""
        if self._openrouter_client is None:
            import os
            api_key = os.getenv("OPENROUTER_API_KEY")
            base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            
            if not api_key:
                raise QQChannelMCPError("未配置OPENROUTER_API_KEY环境变量")
            
            self._openrouter_client = OpenRouterClient(api_key, base_url)
        
        return self._openrouter_client
    
    def get_client_by_provider(self, provider: AIProvider) -> Union[GeminiClient, GitHubModelsClient, CherryStudioClient, OpenRouterClient]:
        """根据提供商获取AI客户端"""
        if provider == AIProvider.GEMINI:
            return self.gemini_client
        elif provider == AIProvider.GITHUB_MODELS:
            return self.models_client
        elif provider == AIProvider.CHERRYSTUDIO:
            return self.cherrystudio_client
        elif provider == AIProvider.OPENROUTER:
            return self.openrouter_client
        else:
            raise QQChannelMCPError(f"不支持的AI提供商: {provider}")
    
    async def get_default_client(self) -> Union[GeminiClient, GitHubModelsClient, CherryStudioClient, OpenRouterClient]:
        """获取默认AI客户端"""
        return self.get_client_by_provider(self.preferred_provider)
    
    async def get_available_client(self) -> Union[GeminiClient, GitHubModelsClient, CherryStudioClient, OpenRouterClient]:
        """获取第一个可用的AI客户端"""
        providers_to_try = [self.preferred_provider]
        
        # 添加其他提供商作为备选
        for provider in AIProvider:
            if provider not in providers_to_try:
                providers_to_try.append(provider)
        
        for provider in providers_to_try:
            try:
                client = self.get_client_by_provider(provider)
                async with client as test_client:
                    if await test_client.test_connection():
                        logger.info(f"使用AI提供商: {provider.value}")
                        return client
            except Exception as e:
                logger.warning(f"AI提供商 {provider.value} 不可用: {e}")
                continue
        
        raise QQChannelMCPError("没有可用的AI客户端")
    
    async def test_all_clients(self) -> Dict[str, bool]:
        """测试所有AI客户端连接"""
        results = {}
        
        # 测试Gemini
        try:
            async with self.gemini_client as client:
                results["gemini"] = await client.test_connection()
        except Exception as e:
            logger.error(f"Gemini客户端测试失败: {e}")
            results["gemini"] = False
        
        # 测试GitHub Models
        try:
            async with self.models_client as client:
                results["github_models"] = await client.test_connection()
        except Exception as e:
            logger.error(f"GitHub Models客户端测试失败: {e}")
            results["github_models"] = False
        
        # 测试CherryStudio
        try:
            async with self.cherrystudio_client as client:
                results["cherrystudio"] = await client.test_connection()
        except Exception as e:
            logger.error(f"CherryStudio客户端测试失败: {e}")
            results["cherrystudio"] = False
        
        # 测试OpenRouter
        try:
            async with self.openrouter_client as client:
                results["openrouter"] = await client.test_connection()
        except Exception as e:
            logger.error(f"OpenRouter客户端测试失败: {e}")
            results["openrouter"] = False
        
        return results
    
    async def test_all_providers(self) -> Dict[str, bool]:
        """测试所有AI提供商连接（别名方法）"""
        return await self.test_all_clients()
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有AI提供商的状态信息"""
        import os
        
        status = {
            "gemini": {
                "configured": bool(os.getenv("GEMINI_API_KEY")),
                "base_url": os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"),
                "available": False
            },
            "github_models": {
                "configured": bool(os.getenv("GITHUB_MODELS_API_KEY")), 
                "base_url": os.getenv("GITHUB_MODELS_BASE_URL", "https://models.github.ai"),
                "available": False
            },
            "cherrystudio": {
                "configured": bool(os.getenv("CHERRYSTUDIO_API_KEY")),
                "base_url": os.getenv("CHERRYSTUDIO_BASE_URL", "https://api.cherrystudio.ai"),
                "available": False
            },
            "openrouter": {
                "configured": bool(os.getenv("OPENROUTER_API_KEY")),
                "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                "available": False
            }
        }
        
        return status
    
    async def auto_configure_provider(self) -> AIProvider:
        """自动配置并选择最佳的AI提供商"""
        status = self.get_provider_status()
        
        # 优先级: OpenRouter > GitHub Models > Gemini > CherryStudio (可根据需要调整)
        provider_priority = [
            (AIProvider.OPENROUTER, "openrouter"),
            (AIProvider.GITHUB_MODELS, "github_models"),
            (AIProvider.GEMINI, "gemini"),
            (AIProvider.CHERRYSTUDIO, "cherrystudio")
        ]
        
        for provider_enum, provider_key in provider_priority:
            if status[provider_key]["configured"]:
                try:
                    client = self.get_client_by_provider(provider_enum)
                    async with client as test_client:
                        if await test_client.test_connection():
                            self.preferred_provider = provider_enum
                            logger.info(f"自动选择AI提供商: {provider_enum.value}")
                            return provider_enum
                except Exception as e:
                    logger.warning(f"AI提供商 {provider_enum.value} 测试失败: {e}")
        
        raise QQChannelMCPError("没有可用的AI提供商，请检查API配置")
