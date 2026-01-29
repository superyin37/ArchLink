"""
Google Gemini 视觉模型引擎
"""

import requests
import logging
from typing import Dict, Any

from spec_locator.llm.base_engine import BaseLLMEngine
from spec_locator.llm.prompt_templates import PromptManager

logger = logging.getLogger(__name__)


class GeminiEngine(BaseLLMEngine):
    """Gemini 视觉模型引擎 - 使用 Google Gemini API"""
    
    # Gemini API 端点模板
    API_ENDPOINT_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "gemini-1.5-pro",
        timeout: int = 30,
        max_retries: int = 2,
        prompt_version: str = "v1"
    ):
        """
        初始化Gemini引擎
        
        Args:
            api_key: Google API密钥
            model: 模型名称 (gemini-1.5-pro, gemini-1.5-flash, gemini-pro-vision)
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            prompt_version: Prompt版本
        """
        super().__init__(api_key, model, timeout, max_retries, prompt_version)
        self.api_endpoint = self.API_ENDPOINT_TEMPLATE.format(model=model)
    
    def _call_api(self, image_base64: str) -> str:
        """
        调用Gemini API
        
        Args:
            image_base64: Base64编码的图片
            
        Returns:
            API响应文本
        """
        # 构建消息 - Gemini格式
        messages = PromptManager.build_messages(
            image_base64, 
            self.prompt_version,
            provider="gemini"
        )
        
        # 构建请求体 - Gemini使用不同的结构
        payload = {
            "contents": messages
        }
        
        # Gemini使用URL参数传递API密钥
        params = {
            "key": self.api_key
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json"
        }
        
        # 发送请求
        response = requests.post(
            self.api_endpoint,
            json=payload,
            params=params,
            headers=headers,
            timeout=self.timeout
        )
        
        # 检查响应
        response.raise_for_status()
        result = response.json()
        
        # 提取内容 - Gemini的响应结构不同
        if "candidates" in result and len(result["candidates"]) > 0:
            candidate = result["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    return parts[0]["text"]
        
        raise ValueError(f"Unexpected API response format: {result}")
