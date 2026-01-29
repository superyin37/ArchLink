"""
大模型响应解析器
"""

import re
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ResponseParser:
    """大模型响应解析器，支持多种格式"""
    
    @staticmethod
    def parse(response_text: str) -> Dict[str, Any]:
        """
        解析大模型响应
        
        Args:
            response_text: 大模型返回的文本
            
        Returns:
            解析后的结构化数据
        """
        # 尝试多种解析方式
        parsers = [
            ResponseParser._parse_json_direct,
            ResponseParser._parse_json_from_markdown,
            ResponseParser._parse_json_from_text,
            ResponseParser._parse_natural_language
        ]
        
        for parser in parsers:
            try:
                result = parser(response_text)
                if result and ResponseParser.validate(result):
                    logger.info(f"Successfully parsed using {parser.__name__}")
                    return result
            except Exception as e:
                logger.debug(f"Parser {parser.__name__} failed: {e}")
                continue
        
        # 所有解析器都失败
        logger.error(f"Failed to parse response: {response_text[:200]}")
        return {
            "spec_code": None,
            "page_code": None,
            "confidence": 0.0,
            "reasoning": "Failed to parse model response"
        }
    
    @staticmethod
    def _parse_json_direct(text: str) -> Optional[Dict]:
        """直接解析JSON"""
        return json.loads(text.strip())
    
    @staticmethod
    def _parse_json_from_markdown(text: str) -> Optional[Dict]:
        """从Markdown代码块中提取JSON"""
        # 匹配 ```json ... ``` 或 ``` ... ```
        pattern = r"```(?:json)?\s*\n(.*?)\n```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        return None
    
    @staticmethod
    def _parse_json_from_text(text: str) -> Optional[Dict]:
        """从文本中提取JSON对象"""
        # 查找第一个完整的JSON对象
        start = text.find('{')
        if start == -1:
            return None
        
        # 简单的大括号匹配
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    json_str = text[start:i+1]
                    return json.loads(json_str)
        return None
    
    @staticmethod
    def _parse_natural_language(text: str) -> Optional[Dict]:
        """从自然语言中提取信息（最后的兜底方案）"""
        # 提取规范编号
        spec_pattern = r'([A-Z]{0,2}\d{2,3}\s*[A-Z]\s*\d{1,3}(?:-\d+)?)'
        spec_matches = re.findall(spec_pattern, text)
        
        # 提取页码
        page_pattern = r'([A-Z]\d{1,3}(?:-\d+)?)'
        page_matches = re.findall(page_pattern, text)
        
        if spec_matches and page_matches:
            return {
                "spec_code": spec_matches[0].replace(' ', ''),
                "page_code": page_matches[0],
                "confidence": 0.5,  # 较低置信度
                "reasoning": "Extracted from natural language"
            }
        return None
    
    @staticmethod
    def validate(data: Dict) -> bool:
        """
        验证解析结果的有效性
        
        Args:
            data: 解析后的数据
            
        Returns:
            是否有效
        """
        required_keys = {"spec_code", "page_code", "confidence"}
        
        # 检查必需字段
        if not all(key in data for key in required_keys):
            return False
        
        # 检查置信度范围
        if not (0.0 <= data["confidence"] <= 1.0):
            return False
        
        return True
