"""
LLM引擎基类 - 定义统一接口
"""

import logging
import base64
import cv2
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from spec_locator.llm.response_parser import ResponseParser

logger = logging.getLogger(__name__)


class BaseLLMEngine(ABC):
    """LLM引擎抽象基类 - 定义统一接口"""
    
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: int = 30,
        max_retries: int = 2,
        prompt_version: str = "v1"
    ):
        """
        初始化引擎
        
        Args:
            api_key: API密钥
            model: 模型名称
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            prompt_version: Prompt版本
        """
        if not api_key:
            raise ValueError(f"{self.__class__.__name__} API key is required")
        
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.prompt_version = prompt_version
        
        logger.info(f"{self.__class__.__name__} initialized: model={model}, timeout={timeout}s")
    
    def recognize(self, image: np.ndarray) -> Dict[str, Any]:
        """
        识别图片中的规范编号和页码
        
        Args:
            image: 输入图像（BGR格式，numpy数组）
            
        Returns:
            {
                "success": True/False,
                "spec_code": "12J2",
                "page_code": "C11",
                "confidence": 0.95,
                "reasoning": "识别依据",
                "raw_response": "原始响应"
            }
        """
        try:
            # 1. 图像转Base64
            image_base64 = self._image_to_base64(image)
            
            # 2. 调用API
            logger.info(f"Calling {self.__class__.__name__} API...")
            raw_response = self._call_api_with_retry(image_base64)
            logger.info(f"API response received: {raw_response[:200]}...")
            
            # 🔍 测试：打印完整的原始响应
            print("\n" + "="*80)
            print("[LLM RAW RESPONSE]")
            print("="*80)
            print(raw_response)
            print("="*80 + "\n")
            
            # 3. 解析响应
            parsed_result = ResponseParser.parse(raw_response)
            
            # 🔍 测试：打印解析后的结果
            print("\n" + "="*80)
            print("[LLM PARSED RESULT]")
            print("="*80)
            print(f"spec_code: {parsed_result.get('spec_code')}")
            print(f"page_code: {parsed_result.get('page_code')}")
            print(f"confidence: {parsed_result.get('confidence')}")
            print(f"reasoning: {parsed_result.get('reasoning')}")
            print("="*80 + "\n")
            
            # 4. 构建返回结果
            result = {
                "success": parsed_result.get("spec_code") is not None and parsed_result.get("page_code") is not None,
                "spec_code": parsed_result.get("spec_code"),
                "page_code": parsed_result.get("page_code"),
                "confidence": parsed_result.get("confidence", 0.0),
                "reasoning": parsed_result.get("reasoning", ""),
                "raw_response": raw_response
            }
            
            logger.info(f"Recognition result: {result['spec_code']} / {result['page_code']} (conf={result['confidence']})")
            return result
            
        except Exception as e:
            logger.error(f"{self.__class__.__name__} recognition failed: {e}", exc_info=True)
            return {
                "success": False,
                "spec_code": None,
                "page_code": None,
                "confidence": 0.0,
                "reasoning": f"Error: {str(e)}",
                "raw_response": ""
            }
    
    def _image_to_base64(self, image: np.ndarray) -> str:
        """
        将numpy图像转换为Base64编码
        
        Args:
            image: numpy数组图像
            
        Returns:
            Base64编码字符串
        """
        # 确保是RGB格式
        if len(image.shape) == 3 and image.shape[2] == 3:
            # OpenCV使用BGR，需要转换为RGB
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 编码为JPEG
        success, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not success:
            raise ValueError("Failed to encode image")
        
        # 转Base64
        return base64.b64encode(buffer).decode('utf-8')
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _call_api_with_retry(self, image_base64: str) -> str:
        """
        调用API（带重试）
        
        Args:
            image_base64: Base64编码的图片
            
        Returns:
            API响应文本
        """
        return self._call_api(image_base64)
    
    @abstractmethod
    def _call_api(self, image_base64: str) -> str:
        """
        调用API的具体实现（子类必须实现）
        
        Args:
            image_base64: Base64编码的图片
            
        Returns:
            API响应文本
        """
        pass
    
    def warmup(self):
        """预热（可选，用于测试连接）"""
        logger.info(f"{self.__class__.__name__} warmup - testing connection...")
