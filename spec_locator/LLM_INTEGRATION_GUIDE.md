# 豆包大模型集成 - 开发指南

## 文档信息
- **版本**: v1.0
- **创建日期**: 2026-01-28
- **目标读者**: 开发人员

---

## 一、开发准备

### 1.1 前置条件

- [x] 了解现有spec_locator项目架构
- [x] 熟悉PaddleOCR识别流程
- [x] 了解FastAPI框架
- [x] 有豆包API使用经验（可参考rag_demo模块）

### 1.2 开发环境

**必需软件**：
- Python 3.8+
- VS Code 或 PyCharm
- Git

**依赖包安装**：
```bash
# 进入项目虚拟环境
cd d:\projects\liuzong\spec_locator
.\.venv\Scripts\Activate.ps1

# 安装新依赖
pip install volcenginesdkarkruntime tenacity
```

### 1.3 获取豆包API密钥

1. 访问：https://console.volcengine.com/ark
2. 创建或获取API密钥
3. 配置环境变量：
   ```bash
   # Windows
   set DOUBAO_API_KEY=your_api_key_here
   
   # Linux/Mac
   export DOUBAO_API_KEY=your_api_key_here
   ```

---

## 二、实施步骤

### Phase 1: 基础模块实现（Day 1-2）

#### Step 1.1: 创建LLM模块目录结构

```bash
mkdir spec_locator\llm
New-Item spec_locator\llm\__init__.py
New-Item spec_locator\llm\doubao_engine.py
New-Item spec_locator\llm\prompt_templates.py
New-Item spec_locator\llm\response_parser.py
```

#### Step 1.2: 实现Prompt模板管理器

**文件**: `spec_locator/llm/prompt_templates.py`

```python
"""
Prompt模板管理
"""

class PromptManager:
    """Prompt模板管理器"""
    
    # 系统提示词
    SYSTEM_PROMPT = """你是一个专业的建筑规范图纸识别专家，擅长从CAD截图中识别规范编号和页码。"""
    
    # 主识别Prompt（版本1）
    RECOGNITION_PROMPT_V1 = """
请仔细分析这张CAD截图，识别其中的：

1. **规范编号**：格式如 12J2、20G908-1、L13J5-1、23J908-8
   - 通常由2-3位数字 + 字母 + 数字组成
   - 可能有字母前缀（如L、苏等地方标准）
   - 可能有短横线和后缀数字

2. **页码**：格式如 C11、C11-2、P23、1-11
   - 通常由1个字母 + 数字组成
   - 可能有短横线和后缀数字
   - 一般与规范编号位置相邻

请严格按照以下JSON格式返回：
```json
{
    "spec_code": "识别到的规范编号",
    "page_code": "识别到的页码",
    "confidence": 0.95,
    "reasoning": "识别依据说明"
}
```

如果无法识别，请返回：
```json
{
    "spec_code": null,
    "page_code": null,
    "confidence": 0.0,
    "reasoning": "无法识别的原因"
}
```
"""
    
    @classmethod
    def get_prompt(cls, version: str = "v1") -> str:
        """
        获取指定版本的Prompt
        
        Args:
            version: Prompt版本号
            
        Returns:
            Prompt文本
        """
        if version == "v1":
            return cls.RECOGNITION_PROMPT_V1
        else:
            raise ValueError(f"Unknown prompt version: {version}")
    
    @classmethod
    def build_messages(cls, image_base64: str, version: str = "v1") -> list:
        """
        构建完整的消息列表
        
        Args:
            image_base64: Base64编码的图片
            version: Prompt版本
            
        Returns:
            消息列表（适用于豆包API）
        """
        return [
            {
                "role": "system",
                "content": cls.SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": cls.get_prompt(version)
                    }
                ]
            }
        ]
```

#### Step 1.3: 实现响应解析器

**文件**: `spec_locator/llm/response_parser.py`

```python
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
```

#### Step 1.4: 实现豆包引擎

**文件**: `spec_locator/llm/doubao_engine.py`

```python
"""
豆包视觉大模型引擎
"""

import os
import logging
import base64
import cv2
import numpy as np
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from volcenginesdkarkruntime import Ark
except ImportError:
    raise ImportError("Please install: pip install volcenginesdkarkruntime")

from spec_locator.llm.prompt_templates import PromptManager
from spec_locator.llm.response_parser import ResponseParser

logger = logging.getLogger(__name__)


class DoubaoEngine:
    """豆包视觉大模型引擎"""
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "doubao-vision-pro",
        timeout: int = 30,
        max_retries: int = 2,
        prompt_version: str = "v1"
    ):
        """
        初始化豆包引擎
        
        Args:
            api_key: API密钥（优先使用参数，否则从环境变量读取）
            model: 模型名称
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            prompt_version: Prompt版本
        """
        self.api_key = api_key or os.getenv("DOUBAO_API_KEY") or os.getenv("ARK_API_KEY")
        if not self.api_key:
            raise ValueError("DOUBAO_API_KEY not set in environment or parameters")
        
        self.client = Ark(api_key=self.api_key)
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.prompt_version = prompt_version
        
        logger.info(f"DoubaoEngine initialized: model={model}, timeout={timeout}s")
    
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
            logger.info("Calling Doubao API...")
            raw_response = self._call_api_with_retry(image_base64)
            logger.info(f"API response received: {raw_response[:200]}...")
            
            # 3. 解析响应
            parsed_result = ResponseParser.parse(raw_response)
            
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
            logger.error(f"DoubaoEngine recognition failed: {e}", exc_info=True)
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
        # 确保是RGB格式（豆包API要求）
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
        调用豆包API（带重试）
        
        Args:
            image_base64: Base64编码的图片
            
        Returns:
            API响应文本
        """
        # 构建消息
        messages = PromptManager.build_messages(image_base64, self.prompt_version)
        
        # 调用API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            timeout=self.timeout
        )
        
        return response.choices[0].message.content
    
    def warmup(self):
        """预热（可选，用于测试连接）"""
        logger.info("DoubaoEngine warmup - testing connection...")
        # 可以发送一个小的测试请求
        pass
```

#### Step 1.5: 创建模块初始化文件

**文件**: `spec_locator/llm/__init__.py`

```python
"""
大模型识别模块
"""

from spec_locator.llm.doubao_engine import DoubaoEngine
from spec_locator.llm.prompt_templates import PromptManager
from spec_locator.llm.response_parser import ResponseParser

__all__ = [
    "DoubaoEngine",
    "PromptManager",
    "ResponseParser"
]
```

#### Step 1.6: 单元测试

**文件**: `spec_locator/tests/test_llm_module.py`

```python
"""
LLM模块单元测试
"""

import pytest
import numpy as np
from spec_locator.llm import DoubaoEngine, ResponseParser, PromptManager


class TestResponseParser:
    """测试响应解析器"""
    
    def test_parse_json_direct(self):
        """测试直接JSON解析"""
        json_str = '{"spec_code": "12J2", "page_code": "C11", "confidence": 0.95}'
        result = ResponseParser.parse(json_str)
        assert result["spec_code"] == "12J2"
        assert result["page_code"] == "C11"
    
    def test_parse_json_from_markdown(self):
        """测试从Markdown提取JSON"""
        markdown_str = """
这是识别结果：
```json
{
    "spec_code": "20G908-1",
    "page_code": "P23",
    "confidence": 0.88
}
```
"""
        result = ResponseParser.parse(markdown_str)
        assert result["spec_code"] == "20G908-1"
        assert result["page_code"] == "P23"
    
    def test_parse_natural_language(self):
        """测试自然语言提取"""
        nl_str = "识别到规范编号为 12J2，页码为 C11"
        result = ResponseParser.parse(nl_str)
        assert result["spec_code"] == "12J2"
        assert result["page_code"] == "C11"


class TestPromptManager:
    """测试Prompt管理器"""
    
    def test_get_prompt_v1(self):
        """测试获取v1 Prompt"""
        prompt = PromptManager.get_prompt("v1")
        assert "规范编号" in prompt
        assert "页码" in prompt
        assert "JSON" in prompt
    
    def test_build_messages(self):
        """测试构建消息列表"""
        image_base64 = "dummy_base64_string"
        messages = PromptManager.build_messages(image_base64, "v1")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"


@pytest.mark.skipif(not os.getenv("DOUBAO_API_KEY"), reason="API key not set")
class TestDoubaoEngine:
    """测试豆包引擎（需要API密钥）"""
    
    def test_initialization(self):
        """测试初始化"""
        engine = DoubaoEngine()
        assert engine.model is not None
        assert engine.client is not None
    
    def test_image_to_base64(self):
        """测试图片Base64编码"""
        # 创建测试图片
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        engine = DoubaoEngine()
        base64_str = engine._image_to_base64(image)
        assert isinstance(base64_str, str)
        assert len(base64_str) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

### Phase 2: Pipeline集成（Day 3）

#### Step 2.1: 添加LLM配置

**文件**: `spec_locator/config/config.py`

在文件末尾添加：

```python
# ===== 大模型配置 =====
class LLMConfig:
    """大模型配置"""
    
    # 基础配置
    ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
    API_KEY = os.getenv("DOUBAO_API_KEY") or os.getenv("ARK_API_KEY")
    MODEL = os.getenv("LLM_MODEL", "doubao-vision-pro")
    
    # 性能配置
    TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))  # 秒
    MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
    
    # 混合模式配置
    AUTO_FALLBACK = os.getenv("LLM_AUTO_FALLBACK", "true").lower() == "true"
    OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.6"))
    
    # Prompt配置
    PROMPT_VERSION = os.getenv("LLM_PROMPT_VERSION", "v1")
    
    @staticmethod
    def validate():
        """验证配置有效性"""
        if LLMConfig.ENABLED and not LLMConfig.API_KEY:
            logger.warning("LLM is enabled but DOUBAO_API_KEY is not set")
            return False
        return True
```

同时更新 `__init__.py` 导出：

```python
from spec_locator.config.config import (
    # ... 现有导出
    LLMConfig,  # 新增
)

__all__ = [
    # ... 现有导出
    "LLMConfig",  # 新增
]
```

#### Step 2.2: 修改Pipeline支持多策略

**文件**: `spec_locator/core/pipeline.py`

在文件开头添加导入：

```python
from spec_locator.config import LLMConfig
from spec_locator.llm import DoubaoEngine
```

修改 `__init__` 方法：

```python
def __init__(
    self,
    use_gpu: bool = False,
    ocr_threshold: float = 0.3,
    max_distance: int = 100,
    data_dir: str = None,
    lazy_ocr: bool = True,
    recognition_method: str = "ocr",  # 新增参数
    llm_api_key: str = None,          # 新增参数
):
    """
    初始化流水线

    Args:
        # ... 现有参数说明
        recognition_method: 识别方式 ("ocr" | "llm" | "auto")
        llm_api_key: 大模型API密钥
    """
    # 现有初始化代码...
    
    # 新增：识别方式配置
    self.recognition_method = recognition_method
    
    # 新增：初始化LLM引擎（如果需要）
    self.llm_engine = None
    if recognition_method in ["llm", "auto"] and LLMConfig.ENABLED:
        try:
            self.llm_engine = DoubaoEngine(
                api_key=llm_api_key or LLMConfig.API_KEY,
                model=LLMConfig.MODEL,
                timeout=LLMConfig.TIMEOUT,
                max_retries=LLMConfig.MAX_RETRIES,
                prompt_version=LLMConfig.PROMPT_VERSION
            )
            logger.info(f"✓ LLM Engine initialized (method={recognition_method})")
        except Exception as e:
            logger.error(f"Failed to initialize LLM engine: {e}")
            if recognition_method == "llm":
                raise  # llm模式必须成功初始化
```

在 `process` 方法前添加路由逻辑：

```python
def process(self, image: np.ndarray) -> Dict[str, Any]:
    """
    处理图像并返回识别结果（支持多种识别方式）

    Args:
        image: 输入图像（BGR 格式）

    Returns:
        包含结果或错误的字典
    """
    # 根据识别方式路由
    if self.recognition_method == "llm":
        return self._process_with_llm(image)
    elif self.recognition_method == "auto":
        return self._process_hybrid(image)
    else:  # "ocr" 或默认
        return self._process_with_ocr(image)

def _process_with_ocr(self, image: np.ndarray) -> Dict[str, Any]:
    """OCR识别流程（原process方法逻辑）"""
    try:
        # 原有的完整识别逻辑...
        # （将原process方法的内容移到这里）
        pass
    except Exception as e:
        logger.error(f"OCR Pipeline error: {e}", exc_info=True)
        return self._error_response(ErrorCode.INTERNAL_ERROR)

def _process_with_llm(self, image: np.ndarray) -> Dict[str, Any]:
    """大模型识别流程（新增）"""
    try:
        if not self.llm_engine:
            return self._error_response(ErrorCode.LLM_NOT_CONFIGURED)
        
        logger.info("Processing with LLM...")
        llm_result = self.llm_engine.recognize(image)
        
        if not llm_result["success"]:
            return {
                "success": False,
                "method": "llm",
                "error_code": ErrorCode.NO_MATCH,
                "message": "LLM failed to recognize spec code or page code",
                "details": llm_result
            }
        
        # 查找对应的PDF文件
        pdf_file = self.file_index.find_file(
            llm_result["spec_code"],
            llm_result["page_code"]
        )
        
        response = {
            "success": True,
            "method": "llm",
            "spec": {
                "code": llm_result["spec_code"],
                "page": llm_result["page_code"],
                "confidence": llm_result["confidence"],
            },
            "metadata": {
                "llm_reasoning": llm_result.get("reasoning", "")
            }
        }
        
        if pdf_file:
            response["file"] = {
                "path": pdf_file,
                "exists": True,
                "download_url": f"/api/download/{llm_result['spec_code']}/{llm_result['page_code']}"
            }
        else:
            response["file"] = {"exists": False}
        
        return response
        
    except Exception as e:
        logger.error(f"LLM Pipeline error: {e}", exc_info=True)
        return self._error_response(ErrorCode.INTERNAL_ERROR)

def _process_hybrid(self, image: np.ndarray) -> Dict[str, Any]:
    """混合识别流程：先OCR，低置信度时尝试LLM（新增）"""
    logger.info("Processing with hybrid strategy...")
    
    # 1. 先尝试OCR
    ocr_result = self._process_with_ocr(image)
    
    # 2. 检查OCR置信度
    ocr_confidence = ocr_result.get("spec", {}).get("confidence", 0.0)
    logger.info(f"OCR confidence: {ocr_confidence}")
    
    # 3. 如果OCR置信度足够高，直接返回
    if ocr_result["success"] and ocr_confidence >= LLMConfig.OCR_CONFIDENCE_THRESHOLD:
        logger.info("OCR confidence is high enough, using OCR result")
        ocr_result["method"] = "ocr"
        return ocr_result
    
    # 4. OCR置信度低，尝试LLM
    logger.info("OCR confidence is low, trying LLM...")
    if self.llm_engine:
        llm_result = self._process_with_llm(image)
        
        if llm_result["success"]:
            llm_result["metadata"]["ocr_confidence"] = ocr_confidence
            llm_result["metadata"]["fallback_reason"] = "low_ocr_confidence"
            return llm_result
    
    # 5. LLM也失败，返回OCR结果（带降级标记）
    logger.warning("LLM also failed, returning OCR result")
    ocr_result["method"] = "ocr"
    ocr_result["metadata"] = {"llm_attempted": True, "llm_failed": True}
    return ocr_result
```

添加新的错误码（在config.py中）：

```python
class ErrorCode(str, Enum):
    # ... 现有错误码
    LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"  # 新增
```

---

### Phase 3: API与前端集成（Day 4）

#### Step 3.1: 修改API接口

**文件**: `spec_locator/api/server.py`

修改 `locate_spec` 函数：

```python
from fastapi import Query  # 添加导入

@app.post("/api/spec-locate")
async def locate_spec(
    file: UploadFile = File(...),
    method: str = Query(
        default="ocr",
        regex="^(ocr|llm|auto)$",
        description="识别方式: ocr-OCR识别, llm-大模型识别, auto-智能切换"
    )
):
    """
    规范定位识别接口（支持多种识别方式）

    Args:
        file: CAD 截图文件
        method: 识别方式 (ocr/llm/auto)

    Returns:
        JSON 响应
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="服务正在初始化中，请稍后重试")
    
    try:
        # 1. 文件验证（保持不变）
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")

        filename = file.filename.lower()
        if not any(filename.endswith(ext) for ext in APIConfig.ALLOWED_EXTENSIONS):
            return _error_response(ErrorCode.INVALID_FILE)

        contents = await file.read()
        if len(contents) > APIConfig.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="File too large")

        # 2. 读取图像（保持不变）
        try:
            nparr = np.frombuffer(contents, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return _error_response(ErrorCode.INVALID_FILE)
        except Exception as e:
            logger.error(f"Failed to decode image: {e}")
            return _error_response(ErrorCode.INVALID_FILE)

        # 3. 根据method参数设置识别方式
        original_method = pipeline.recognition_method
        pipeline.recognition_method = method
        
        # 4. 调用流水线处理
        logger.info(f"Processing file: {filename} with method: {method}")
        result = pipeline.process(image)
        
        # 恢复原始设置
        pipeline.recognition_method = original_method

        return JSONResponse(content=result)

    except HTTPException as e:
        logger.error(f"HTTP exception: {e}")
        return JSONResponse(
            status_code=e.status_code,
            content={
                "success": False,
                "error_code": "INVALID_REQUEST",
                "message": e.detail,
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return _error_response(ErrorCode.INTERNAL_ERROR)
```

#### Step 3.2: 修改前端HTML

**文件**: `spec_locator/api/demo.html`

在上传区域后添加识别方式选择器（约在第100行左右）：

```html
<!-- 在 upload-area 后添加 -->
<div class="method-selector">
    <h3>选择识别方式</h3>
    <div class="radio-group">
        <label class="radio-card">
            <input type="radio" name="method" value="ocr" checked>
            <div class="card-content">
                <div class="card-icon">⚡</div>
                <div class="card-title">OCR识别</div>
                <div class="card-desc">快速识别，适合清晰图像</div>
                <div class="card-badge recommended">推荐</div>
            </div>
        </label>
        
        <label class="radio-card">
            <input type="radio" name="method" value="llm">
            <div class="card-content">
                <div class="card-icon">🤖</div>
                <div class="card-title">大模型识别</div>
                <div class="card-desc">智能识别，适合复杂场景</div>
                <div class="card-badge accuracy">高精度</div>
            </div>
        </label>
        
        <label class="radio-card">
            <input type="radio" name="method" value="auto">
            <div class="card-content">
                <div class="card-icon">🎯</div>
                <div class="card-title">智能切换</div>
                <div class="card-desc">自动选择最佳识别方式</div>
                <div class="card-badge best">最佳</div>
            </div>
        </label>
    </div>
</div>
```

添加样式（在 `<style>` 标签内）：

```css
/* 识别方式选择器样式 */
.method-selector {
    margin: 30px 0;
}

.method-selector h3 {
    font-size: 18px;
    margin-bottom: 15px;
    color: #333;
}

.radio-group {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
}

.radio-card {
    cursor: pointer;
    display: block;
}

.radio-card input[type="radio"] {
    display: none;
}

.card-content {
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    transition: all 0.3s;
    background: white;
    position: relative;
}

.radio-card input[type="radio"]:checked + .card-content {
    border-color: #667eea;
    background: #f0f2ff;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

.card-icon {
    font-size: 36px;
    margin-bottom: 10px;
}

.card-title {
    font-size: 16px;
    font-weight: bold;
    color: #333;
    margin-bottom: 5px;
}

.card-desc {
    font-size: 12px;
    color: #666;
    margin-bottom: 10px;
}

.card-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: bold;
}

.card-badge.recommended {
    background: #ffd700;
    color: #333;
}

.card-badge.accuracy {
    background: #ff6b6b;
    color: white;
}

.card-badge.best {
    background: #51cf66;
    color: white;
}

.radio-card:hover .card-content {
    border-color: #667eea;
    transform: translateY(-2px);
}
```

修改JavaScript提交逻辑（在 `<script>` 标签内）：

```javascript
// 修改现有的 uploadFile 函数
async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    if (!fileInput.files[0]) {
        showNotification('请先选择文件', 'error');
        return;
    }
    
    // 获取选中的识别方式
    const methodRadios = document.getElementsByName('method');
    let method = 'ocr';
    for (const radio of methodRadios) {
        if (radio.checked) {
            method = radio.value;
            break;
        }
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    // 显示加载状态（根据method显示不同提示）
    const loadingMessages = {
        'ocr': '正在快速识别中...',
        'llm': '大模型分析中，请稍候（可能需要3-5秒）...',
        'auto': '智能识别中...'
    };
    showLoading(loadingMessages[method]);
    
    try {
        const response = await fetch(`http://localhost:8002/api/spec-locate?method=${method}`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        hideLoading();
        displayResult(result);
        
    } catch (error) {
        hideLoading();
        showNotification('识别失败: ' + error.message, 'error');
    }
}

function displayResult(result) {
    // 修改现有的displayResult函数，显示method信息
    const resultArea = document.querySelector('.result-area');
    const resultCard = document.querySelector('.result-card');
    
    if (result.success) {
        const methodLabels = {
            'ocr': 'OCR识别',
            'llm': '大模型识别',
            'auto': '智能识别'
        };
        
        resultCard.innerHTML = `
            <div class="result-header">
                <h2>✓ 识别成功</h2>
                <span class="method-badge">${methodLabels[result.method] || result.method}</span>
            </div>
            <div class="result-content">
                <div class="result-item">
                    <span class="label">规范编号：</span>
                    <span class="value">${result.spec.code}</span>
                </div>
                <div class="result-item">
                    <span class="label">页码：</span>
                    <span class="value">${result.spec.page}</span>
                </div>
                <div class="result-item">
                    <span class="label">置信度：</span>
                    <span class="value">${(result.spec.confidence * 100).toFixed(1)}%</span>
                </div>
                ${result.metadata?.llm_reasoning ? `
                <div class="result-item">
                    <span class="label">识别依据：</span>
                    <span class="value">${result.metadata.llm_reasoning}</span>
                </div>
                ` : ''}
                ${result.file?.exists ? `
                <a href="${result.file.download_url}" class="download-btn" target="_blank">
                    📥 下载PDF文件
                </a>
                ` : ''}
            </div>
        `;
    } else {
        // 错误显示逻辑...
    }
    
    resultArea.style.display = 'block';
}

// 添加method badge样式
```

添加额外CSS：

```css
.method-badge {
    display: inline-block;
    padding: 5px 12px;
    background: rgba(255, 255, 255, 0.3);
    border-radius: 15px;
    font-size: 12px;
    font-weight: bold;
}

.result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
```

---

### Phase 4: 配置与文档（Day 5）

#### Step 4.1: 创建环境变量示例文件

**文件**: `spec_locator/.env.example`

```bash
# ===== 基础配置 =====
DEBUG=false
LOG_LEVEL=INFO

# ===== 数据目录 =====
SPEC_DATA_DIR=../output_pages

# ===== API配置 =====
API_HOST=0.0.0.0
API_PORT=8002
API_WORKERS=4

# ===== OCR配置 =====
OCR_USE_GPU=false
OCR_PRECISION=fp32
OCR_CONF_THRESHOLD=0.3
OCR_LAZY_LOAD=true
OCR_WARMUP_ON_STARTUP=false

# ===== 大模型配置（新增）=====
LLM_ENABLED=true
DOUBAO_API_KEY=your_doubao_api_key_here
LLM_MODEL=doubao-vision-pro
LLM_TIMEOUT=30
LLM_MAX_RETRIES=2

# 混合模式配置
LLM_AUTO_FALLBACK=true
OCR_CONFIDENCE_THRESHOLD=0.6

# Prompt版本
LLM_PROMPT_VERSION=v1
```

#### Step 4.2: 更新README

**文件**: `spec_locator/LLM_README.md` (新建使用说明)

```markdown
# 大模型识别功能使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install volcenginesdkarkruntime tenacity
```

### 2. 配置API密钥

```bash
# 方式1：环境变量
export DOUBAO_API_KEY=your_api_key_here

# 方式2：.env文件
echo "DOUBAO_API_KEY=your_api_key_here" >> .env
```

### 3. 启动服务

```bash
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002
```

### 4. 访问演示页面

打开浏览器：http://localhost:8002/docs
或使用演示页面：file:///D:/projects/liuzong/spec_locator/api/demo.html

## 使用方式

### 方式1：通过前端界面

1. 打开demo.html
2. 选择识别方式（OCR/大模型/智能切换）
3. 上传CAD截图
4. 查看识别结果

### 方式2：通过API调用

```python
import requests

url = "http://localhost:8002/api/spec-locate"
files = {"file": open("screenshot.png", "rb")}
params = {"method": "llm"}  # 或 "ocr" / "auto"

response = requests.post(url, files=files, params=params)
result = response.json()
print(result)
```

## 识别方式对比

| 方式 | 速度 | 准确率 | 适用场景 | 成本 |
|-----|------|-------|---------|-----|
| OCR | ⚡ 快 | 中等 | 清晰标准图像 | 免费 |
| 大模型 | 🐢 慢 | 高 | 复杂模糊图像 | 付费 |
| 智能切换 | ⚖️ 适中 | 高 | 通用场景 | 按需 |

## 配置说明

详见 `.env.example` 文件

## 常见问题

### Q: 大模型识别失败怎么办？
A: 系统会自动降级到OCR识别（auto模式下）

### Q: 如何提高识别准确率？
A: 1) 使用大模型识别 2) 确保图片清晰 3) 调整Prompt版本

### Q: API成本如何控制？
A: 默认使用OCR，仅在需要时选择大模型

## 更多信息

详见：
- 设计文档：LLM_INTEGRATION_DESIGN.md
- 开发指南：LLM_INTEGRATION_GUIDE.md
```

---

## 三、测试与验证

### 3.1 单元测试运行

```bash
cd spec_locator
pytest tests/test_llm_module.py -v
```

### 3.2 集成测试

```python
# tests/integration/test_full_flow.py
import cv2
import numpy as np

def test_llm_recognition_flow():
    """测试完整的LLM识别流程"""
    # 加载测试图片
    image = cv2.imread("test_images/sample.png")
    
    # 初始化Pipeline
    pipeline = SpecLocatorPipeline(recognition_method="llm")
    
    # 执行识别
    result = pipeline.process(image)
    
    # 验证结果
    assert result["success"] == True
    assert result["spec"]["code"] is not None
    assert result["spec"]["page"] is not None
```

### 3.3 手动测试清单

- [ ] OCR模式：上传清晰图片，验证识别
- [ ] LLM模式：上传模糊图片，验证识别
- [ ] Auto模式：上传不同质量图片，验证切换逻辑
- [ ] 错误处理：测试API密钥错误、超时等
- [ ] 前端交互：验证UI选择和结果显示

---

## 四、部署与发布

### 4.1 部署前检查

```bash
# 1. 检查依赖
pip list | grep -E "volcengine|tenacity"

# 2. 验证配置
python -c "from spec_locator.config import LLMConfig; print(LLMConfig.validate())"

# 3. 测试API连接
python -c "from spec_locator.llm import DoubaoEngine; e = DoubaoEngine(); print('OK')"
```

### 4.2 启动服务

```bash
# 方式1：直接启动
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002

# 方式2：使用启动脚本
./start_demo.bat
```

### 4.3 健康检查

```bash
curl http://localhost:8002/health
```

预期返回：
```json
{
    "status": "ok",
    "index_stats": {...},
    "ocr_loaded": true,
    "llm_enabled": true
}
```

---

## 五、故障排查

### 5.1 常见问题

#### 问题1: ModuleNotFoundError: No module named 'volcenginesdkarkruntime'

**解决**：
```bash
pip install volcenginesdkarkruntime
```

#### 问题2: LLM_NOT_CONFIGURED 错误

**原因**：API密钥未配置

**解决**：
```bash
export DOUBAO_API_KEY=your_key
# 或在.env文件中配置
```

#### 问题3: LLM_TIMEOUT 超时

**原因**：网络慢或模型响应慢

**解决**：
- 增加超时时间：`LLM_TIMEOUT=60`
- 检查网络连接
- 切换到OCR模式

#### 问题4: 响应解析失败

**原因**：大模型返回格式不符合预期

**解决**：
- 检查`raw_response`字段
- 调整Prompt版本
- 查看日志中的解析详情

### 5.2 日志分析

```bash
# 查看最近的错误日志
tail -f logs/app.log | grep -E "ERROR|LLM"

# 查看识别流程
tail -f logs/app.log | grep -E "Processing with|recognition"
```

---

## 六、性能优化建议

1. **并发控制**：限制LLM同时请求数（避免配额超限）
2. **结果缓存**：相同图片避免重复调用（可选）
3. **超时保护**：设置合理的超时时间
4. **降级策略**：确保LLM失败时能正常工作

---

## 七、后续迭代计划

### 短期（1-2周）
- [ ] 收集用户反馈，优化Prompt
- [ ] 增加更多测试用例
- [ ] 完善错误提示信息

### 中期（1-2个月）
- [ ] 实现结果缓存
- [ ] 添加识别历史记录
- [ ] 优化前端交互体验

### 长期（3-6个月）
- [ ] 探索更多大模型
- [ ] 实现智能路由算法
- [ ] 考虑部署本地模型

---

## 附录：开发资源

### 相关文档
- [豆包API文档](https://www.volcengine.com/docs/82379/1298454)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Tenacity文档](https://tenacity.readthedocs.io/)

### 代码示例
见 `spec_locator/examples/llm_recognition_example.py`

### 联系方式
如有问题，请提交Issue或联系开发团队

---

**最后更新**: 2026-01-28
