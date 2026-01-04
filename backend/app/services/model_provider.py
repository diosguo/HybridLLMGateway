import httpx
import json
from app.db import models
from abc import ABC, abstractmethod

class BaseModelProvider(ABC):
    """模型供应商基类"""
    
    @abstractmethod
    async def generate(self, model_config: models.ModelConfig, prompt: str, params: dict) -> str:
        """生成文本"""
        pass

class OpenAIProvider(BaseModelProvider):
    """OpenAI模型供应商"""
    
    async def generate(self, model_config: models.ModelConfig, prompt: str, params: dict) -> str:
        headers = {
            "Authorization": f"Bearer {model_config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model_config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": params.get("max_tokens", model_config.max_tokens),
            "temperature": params.get("temperature", model_config.temperature)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{model_config.base_url or 'https://api.openai.com'}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

class AnthropicProvider(BaseModelProvider):
    """Anthropic模型供应商"""
    
    async def generate(self, model_config: models.ModelConfig, prompt: str, params: dict) -> str:
        headers = {
            "x-api-key": model_config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": model_config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": params.get("max_tokens", model_config.max_tokens),
            "temperature": params.get("temperature", model_config.temperature)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{model_config.base_url or 'https://api.anthropic.com'}/v1/messages",
                headers=headers,
                json=data,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]

class GeminiProvider(BaseModelProvider):
    """Gemini模型供应商"""
    
    async def generate(self, model_config: models.ModelConfig, prompt: str, params: dict) -> str:
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": params.get("max_tokens", model_config.max_tokens),
                "temperature": params.get("temperature", model_config.temperature)
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{model_config.base_url or 'https://generativelanguage.googleapis.com'}/v1beta/models/{model_config.model_name}:generateContent?key={model_config.api_key}",
                headers=headers,
                json=data,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]

class DeepSeekProvider(BaseModelProvider):
    """DeepSeek模型供应商"""
    
    async def generate(self, model_config: models.ModelConfig, prompt: str, params: dict) -> str:
        headers = {
            "Authorization": f"Bearer {model_config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model_config.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": params.get("max_tokens", model_config.max_tokens),
            "temperature": params.get("temperature", model_config.temperature)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{model_config.base_url or 'https://api.deepseek.com'}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

class ModelProviderService:
    """模型供应商服务，统一管理不同的模型供应商"""
    
    def __init__(self):
        self.providers = {
            models.ModelProvider.OPENAI: OpenAIProvider(),
            models.ModelProvider.ANTHROPIC: AnthropicProvider(),
            models.ModelProvider.GEMINI: GeminiProvider(),
            models.ModelProvider.DEEPSEEK: DeepSeekProvider()
        }
    
    async def generate(self, model_config: models.ModelConfig, prompt: str, params: str) -> str:
        """生成文本，统一调用接口"""
        try:
            # 解析params字符串为字典
            params_dict = json.loads(params) if isinstance(params, str) else params
            
            # 获取对应的供应商
            provider = self.providers.get(model_config.provider)
            if not provider:
                raise ValueError(f"Unsupported model provider: {model_config.provider}")
            
            # 调用生成方法
            return await provider.generate(model_config, prompt, params_dict)
        except Exception as e:
            raise Exception(f"Model generation failed: {str(e)}")
