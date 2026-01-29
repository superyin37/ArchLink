"""
ChatGPT/OpenAI 视觉模型引擎
"""

import requests
import logging
from typing import Dict, Any

from spec_locator.llm.base_engine import BaseLLMEngine
from spec_locator.llm.prompt_templates import PromptManager

logger = logging.getLogger(__name__)


class ChatGPTEngine(BaseLLMEngine):
    """ChatGPT 视觉模型引擎 - 使用 OpenAI API"""
    
    # OpenAI API 端点
    API_ENDPOINT = "https://api.openai.com/v1/chat/completions"
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-4o",
        timeout: int = 30,
        max_retries: int = 2,
        prompt_version: str = "v1"
    ):
        """
        初始化ChatGPT引擎
        
        Args:
            api_key: OpenAI API密钥
            model: 模型名称 (gpt-4o, gpt-4-vision-preview, gpt-4-turbo)
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            prompt_version: Prompt版本
        """
        super().__init__(api_key, model, timeout, max_retries, prompt_version)
    
    def _call_api(self, image_base64: str) -> str:
        """
        调用OpenAI API
        
        Args:
            image_base64: Base64编码的图片
            
        Returns:
            API响应文本
        """
        # 构建消息 - OpenAI格式
        messages = PromptManager.build_messages(
            image_base64, 
            self.prompt_version,
            provider="openai"
        )
        
        # 构建请求体
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1000
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 发送请求
        response = requests.post(
            self.API_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=self.timeout
        )
        
        # 检查响应
        response.raise_for_status()
        result = response.json()
        
        # 提取内容
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            raise ValueError(f"Unexpected API response format: {result}")
