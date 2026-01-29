# 豆包大模型集成设计文档

## 文档信息
- **版本**: v1.0
- **创建日期**: 2026-01-28
- **状态**: 设计阶段

---

## 一、背景与目标

### 1.1 背景
当前规范定位系统使用 PaddleOCR 进行图像识别，在清晰、标准的CAD截图上表现良好。但在以下场景存在局限：
- 模糊或低分辨率图片
- 手写标注或非标准字体
- 倾斜或扭曲的图像
- 复杂背景或干扰线条

### 1.2 目标
集成豆包视觉大模型作为补充识别方案，提供：
1. **多种识别方式**：OCR、大模型、智能切换
2. **更高准确率**：处理复杂场景
3. **用户可选**：前端提供选择界面
4. **向后兼容**：不破坏现有OCR功能

### 1.3 预期收益
- **准确率提升**：复杂场景识别率提升 30-50%
- **用户体验**：提供多种识别选项，满足不同需求
- **技术前瞻**：探索大模型在工程领域的应用

---

## 二、可行性分析

### 2.1 技术可行性 ✅

#### 现有基础
- ✅ 项目已使用豆包API（rag_demo模块）
- ✅ 清晰的模块化架构（便于扩展）
- ✅ FastAPI异步框架（支持并发）
- ✅ 前端已有文件上传功能

#### 技术风险
| 风险项 | 影响 | 应对方案 |
|-------|------|---------|
| API稳定性 | 中 | 实现重试机制、降级策略 |
| 响应延迟 | 低 | 前端显示加载状态、设置合理超时 |
| 成本控制 | 中 | 默认使用OCR，按需调用LLM |
| Prompt工程 | 低 | 充分测试，迭代优化 |

### 2.2 业务可行性 ✅

#### 使用场景
1. **OCR失败场景**：自动降级到大模型
2. **高精度需求**：用户主动选择大模型
3. **测试对比**：开发者对比两种方式

#### 成本估算
- **豆包API**：约 ¥0.002-0.01/次（根据模型和图片大小）
- **预期调用量**：假设日均100次 → 月成本 ¥6-30
- **结论**：成本可控，在预算范围内

### 2.3 实施可行性 ✅

#### 开发工作量
- **Phase 1-2（核心）**：3-5人日
- **Phase 3-4（界面）**：1-2人日
- **测试与文档**：2-3人日
- **总计**：6-10人日（1-2周）

---

## 三、架构设计

### 3.1 整体架构

```
┌────────────────────────────────────────────────────────────┐
│                    Frontend Layer                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  识别方式选择组件                                     │  │
│  │  • OCR识别（快速，适合清晰图像）                     │  │
│  │  • 大模型识别（智能，适合复杂场景）                  │  │
│  │  • 智能切换（自动选择最佳方式）                      │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                            │
                            ↓ HTTP POST
┌────────────────────────────────────────────────────────────┐
│                      API Layer                             │
│  POST /api/spec-locate?method=ocr|llm|auto                 │
│  • 请求验证与参数解析                                       │
│  • 文件上传处理                                            │
│  • 响应格式统一                                            │
└────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌────────────────────────────────────────────────────────────┐
│                 Business Logic Layer                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         SpecLocatorPipeline (核心流水线)             │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │        RecognitionRouter (识别路由器)          │  │  │
│  │  │  • 根据method参数选择识别策略                  │  │  │
│  │  │  • 策略模式实现，易于扩展                      │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │              │                          │              │  │
│  │              ↓                          ↓              │  │
│  │  ┌───────────────────┐    ┌───────────────────────┐  │  │
│  │  │ OCR Strategy      │    │   LLM Strategy        │  │  │
│  │  │ (现有逻辑)        │    │   (新增)              │  │  │
│  │  │ • 图像预处理      │    │ • 图片Base64编码      │  │  │
│  │  │ • PaddleOCR识别   │    │ • 调用豆包API         │  │  │
│  │  │ • 文本框解析      │    │ • JSON响应解析        │  │  │
│  │  │ • 规范/页码提取   │    │ • 置信度计算          │  │  │
│  │  └───────────────────┘    └───────────────────────┘  │  │
│  │              │                          │              │  │
│  │              └──────────┬───────────────┘              │  │
│  │                         ↓                              │  │
│  │              ┌────────────────────┐                    │  │
│  │              │  Result Formatter  │                    │  │
│  │              │  • 统一返回格式    │                    │  │
│  │              │  • 文件路径查找    │                    │  │
│  │              └────────────────────┘                    │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ OCR Engine   │  │ LLM Engine   │  │  File Index     │  │
│  │ (PaddleOCR)  │  │ (Doubao API) │  │  (现有)         │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### 3.2 模块划分

#### 新增模块
```
spec_locator/
├── llm/                                    # 新增：大模型模块
│   ├── __init__.py
│   ├── doubao_engine.py                    # 豆包API封装
│   ├── prompt_templates.py                 # Prompt模板管理
│   └── response_parser.py                  # 响应解析器
│
├── core/
│   ├── pipeline.py                         # 修改：增加策略路由
│   └── recognition_strategy.py             # 新增：策略接口
│
├── api/
│   └── server.py                           # 修改：增加method参数
│
└── config/
    └── config.py                           # 修改：增加LLM配置类
```

### 3.3 数据流设计

#### 3.3.1 OCR识别流程（现有）
```
图片上传 → 预处理 → PaddleOCR → 文本框列表 
  → 规范编号解析 → 页码解析 → 置信度评估 
  → 文件查找 → 返回结果
```

#### 3.3.2 大模型识别流程（新增）
```
图片上传 → Base64编码 → 豆包API调用 
  → JSON响应解析 → 格式验证 → 置信度评估 
  → 文件查找 → 返回结果
```

#### 3.3.3 混合识别流程（新增）
```
图片上传 → 先执行OCR流程
  ↓
判断OCR置信度
  ├─ 置信度 ≥ 阈值 → 直接返回OCR结果
  └─ 置信度 < 阈值 → 执行大模型流程 → 返回最佳结果
```

---

## 四、详细设计

### 4.1 核心类设计

#### 4.1.1 RecognitionStrategy (策略接口)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np

class RecognitionStrategy(ABC):
    """识别策略抽象基类"""
    
    @abstractmethod
    def recognize(self, image: np.ndarray) -> Dict[str, Any]:
        """
        执行识别
        
        Args:
            image: 输入图像（BGR格式）
            
        Returns:
            统一格式的识别结果字典
        """
        pass
    
    @abstractmethod
    def warmup(self):
        """预热模型/引擎"""
        pass
```

#### 4.1.2 DoubaoEngine (豆包引擎)

```python
class DoubaoEngine:
    """豆包视觉大模型引擎"""
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "doubao-vision-pro",
        timeout: int = 30,
        max_retries: int = 2
    ):
        """
        初始化豆包引擎
        
        Args:
            api_key: API密钥（从环境变量或直接传入）
            model: 模型名称
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
        """
        
    def recognize(self, image: np.ndarray) -> Dict[str, Any]:
        """
        识别图片中的规范编号和页码
        
        Args:
            image: 输入图像
            
        Returns:
            {
                "success": True,
                "spec_code": "12J2",
                "page_code": "C11",
                "confidence": 0.95,
                "reasoning": "识别依据",
                "raw_response": "原始响应"
            }
        """
        
    def _image_to_base64(self, image: np.ndarray) -> str:
        """将图像转换为Base64编码"""
        
    def _build_prompt(self) -> str:
        """构建Prompt"""
        
    def _call_api(self, image_base64: str) -> str:
        """调用豆包API"""
        
    def _parse_response(self, response: str) -> Dict:
        """解析API响应"""
```

#### 4.1.3 PromptManager (Prompt管理)

```python
class PromptManager:
    """Prompt模板管理器"""
    
    SYSTEM_PROMPT = """你是一个专业的建筑规范图纸识别专家。"""
    
    RECOGNITION_PROMPT_V1 = """
    请仔细分析这张CAD截图，识别其中的：
    1. 规范编号（如：12J2、20G908-1、L13J5-1）
    2. 页码（如：C11、C11-2、P23）
    
    返回JSON格式：
    {
        "spec_code": "规范编号",
        "page_code": "页码",
        "confidence": 0.0-1.0,
        "reasoning": "识别依据"
    }
    """
    
    @classmethod
    def get_prompt(cls, version: str = "v1") -> str:
        """获取指定版本的Prompt"""
        
    @classmethod
    def format_prompt(cls, template: str, **kwargs) -> str:
        """格式化Prompt模板"""
```

#### 4.1.4 ResponseParser (响应解析器)

```python
class ResponseParser:
    """大模型响应解析器"""
    
    @staticmethod
    def parse(response_text: str) -> Dict[str, Any]:
        """
        解析大模型响应，支持多种格式
        
        Args:
            response_text: 大模型返回的文本
            
        Returns:
            解析后的结构化数据
        """
        
    @staticmethod
    def _extract_json(text: str) -> Dict:
        """从文本中提取JSON"""
        
    @staticmethod
    def _parse_natural_language(text: str) -> Dict:
        """从自然语言中提取信息"""
        
    @staticmethod
    def validate(data: Dict) -> bool:
        """验证解析结果的有效性"""
```

### 4.2 Pipeline增强设计

```python
class SpecLocatorPipeline:
    """增强后的规范定位流水线"""
    
    def __init__(
        self,
        recognition_method: str = "ocr",  # "ocr" | "llm" | "auto"
        llm_api_key: str = None,
        llm_model: str = None,
        ocr_confidence_threshold: float = 0.6,
        **kwargs
    ):
        """
        初始化流水线
        
        Args:
            recognition_method: 识别方式
            llm_api_key: 大模型API密钥
            llm_model: 大模型名称
            ocr_confidence_threshold: OCR置信度阈值（用于auto模式）
        """
        # 初始化OCR策略（现有）
        self.ocr_strategy = OCRRecognitionStrategy(...)
        
        # 初始化LLM策略（新增）
        if recognition_method in ["llm", "auto"]:
            self.llm_strategy = LLMRecognitionStrategy(
                api_key=llm_api_key,
                model=llm_model
            )
        
        self.recognition_method = recognition_method
        self.ocr_confidence_threshold = ocr_confidence_threshold
    
    def process(self, image: np.ndarray) -> Dict[str, Any]:
        """
        处理图像并返回识别结果
        
        根据recognition_method路由到不同的策略
        """
        if self.recognition_method == "ocr":
            return self._process_with_ocr(image)
        elif self.recognition_method == "llm":
            return self._process_with_llm(image)
        elif self.recognition_method == "auto":
            return self._process_hybrid(image)
        else:
            raise ValueError(f"Unknown method: {self.recognition_method}")
    
    def _process_with_ocr(self, image: np.ndarray) -> Dict:
        """OCR识别流程（保持现有逻辑）"""
        
    def _process_with_llm(self, image: np.ndarray) -> Dict:
        """大模型识别流程（新增）"""
        
    def _process_hybrid(self, image: np.ndarray) -> Dict:
        """
        混合识别流程（新增）
        1. 先尝试OCR
        2. 如果置信度低，再尝试LLM
        3. 返回最优结果
        """
```

### 4.3 API接口设计

#### 4.3.1 请求参数

```python
@app.post("/api/spec-locate")
async def locate_spec(
    file: UploadFile = File(..., description="CAD截图文件"),
    method: str = Query(
        default="ocr",
        regex="^(ocr|llm|auto)$",
        description="识别方式: ocr-OCR识别, llm-大模型识别, auto-智能切换"
    )
):
    """规范定位识别接口（支持多种识别方式）"""
```

#### 4.3.2 响应格式

**成功响应**：
```json
{
    "success": true,
    "method": "llm",  // 实际使用的识别方式
    "spec": {
        "code": "12J2",
        "page": "C11",
        "confidence": 0.95
    },
    "file": {
        "path": "D:\\...\\12J2\\12J2_C11.pdf",
        "exists": true,
        "download_url": "/api/download/12J2/C11"
    },
    "candidates": [...],  // 候选结果
    "metadata": {
        "ocr_confidence": 0.45,  // auto模式：显示OCR置信度
        "llm_reasoning": "识别依据"  // llm模式：显示推理过程
    }
}
```

**错误响应**：
```json
{
    "success": false,
    "method": "llm",
    "error_code": "LLM_API_ERROR",
    "message": "大模型API调用失败",
    "fallback": {
        "used": true,
        "method": "ocr",
        "result": {...}  // OCR降级结果
    }
}
```

### 4.4 配置设计

#### 4.4.1 配置类

```python
class LLMConfig:
    """大模型配置"""
    
    # 基础配置
    ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
    API_KEY = os.getenv("DOUBAO_API_KEY") or os.getenv("ARK_API_KEY")
    MODEL = os.getenv("LLM_MODEL", "doubao-vision-pro")
    
    # 性能配置
    TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))  # 秒
    MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
    MAX_CONCURRENT = int(os.getenv("LLM_MAX_CONCURRENT", "3"))  # 最大并发数
    
    # 混合模式配置
    AUTO_FALLBACK = os.getenv("LLM_AUTO_FALLBACK", "true").lower() == "true"
    OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.6"))
    
    # Prompt配置
    PROMPT_VERSION = os.getenv("LLM_PROMPT_VERSION", "v1")
    
    # 成本控制
    ENABLE_CACHE = os.getenv("LLM_ENABLE_CACHE", "false").lower() == "true"
    CACHE_TTL = int(os.getenv("LLM_CACHE_TTL", "3600"))  # 缓存时间（秒）
    
    @staticmethod
    def validate():
        """验证配置有效性"""
        if LLMConfig.ENABLED and not LLMConfig.API_KEY:
            raise ValueError("LLM_ENABLED=true but DOUBAO_API_KEY not set")
```

#### 4.4.2 环境变量配置

**.env 示例**：
```bash
# ===== 大模型配置 =====
LLM_ENABLED=true
DOUBAO_API_KEY=your_api_key_here
LLM_MODEL=doubao-vision-pro
LLM_TIMEOUT=30
LLM_MAX_RETRIES=2

# 混合模式配置
LLM_AUTO_FALLBACK=true
OCR_CONFIDENCE_THRESHOLD=0.6

# Prompt版本
LLM_PROMPT_VERSION=v1

# ===== OCR配置（保持不变）=====
OCR_LAZY_LOAD=true
OCR_CONF_THRESHOLD=0.3
```

### 4.5 Prompt工程

#### 4.5.1 Prompt设计原则

1. **明确任务**：清晰描述识别目标（规范编号 + 页码）
2. **提供示例**：给出正确格式示例
3. **输出格式**：要求JSON格式，便于解析
4. **容错处理**：提供无法识别时的返回格式
5. **推理过程**：要求说明识别依据（可选）

#### 4.5.2 Prompt模板 v1

```python
SPEC_RECOGNITION_PROMPT_V1 = """
你是一个专业的建筑规范图纸识别专家。请仔细分析这张CAD截图，识别其中的规范编号和页码。

【识别目标】
1. **规范编号**：格式如 12J2、20G908-1、L13J5-1、23J908-8
   - 通常由2-3位数字 + 字母 + 数字组成
   - 可能有字母前缀（如L、苏等地方标准）
   - 可能有短横线和后缀数字（如 -1、-8）

2. **页码**：格式如 C11、C11-2、P23、1-11
   - 通常由1个字母 + 数字组成
   - 可能有短横线和后缀数字
   - 一般与规范编号位置相邻

【识别规则】
- 规范编号通常在图纸左上角或右上角
- 页码通常在规范编号附近
- 注意区分相似字符：数字0与字母O、数字1与字母I、数字5与字母S

【输出格式】
请严格按照以下JSON格式返回：
```json
{
    "spec_code": "识别到的规范编号",
    "page_code": "识别到的页码",
    "confidence": 0.95,
    "reasoning": "简要说明识别依据，如：在图纸左上角识别到规范编号12J2，右侧紧邻位置识别到页码C11"
}
```

如果无法识别，请返回：
```json
{
    "spec_code": null,
    "page_code": null,
    "confidence": 0.0,
    "reasoning": "无法识别的具体原因"
}
```

请现在开始分析图片。
"""
```

#### 4.5.3 Prompt模板 v2（简化版）

```python
SPEC_RECOGNITION_PROMPT_V2 = """
分析这张CAD截图，识别：
1. 规范编号（如12J2、20G908-1）
2. 页码（如C11、P23）

以JSON格式返回：
{
    "spec_code": "规范编号",
    "page_code": "页码",
    "confidence": 0.0-1.0
}

如无法识别则返回null值和confidence=0。
"""
```

---

## 五、错误处理设计

### 5.1 错误码扩展

```python
class ErrorCode(str, Enum):
    # ===== 现有错误码 =====
    NO_TEXT = "NO_TEXT"
    NO_SPEC_CODE = "NO_SPEC_CODE"
    NO_PAGE_CODE = "NO_PAGE_CODE"
    NO_MATCH = "NO_MATCH"
    FILE_NOT_FOUND_IN_DB = "FILE_NOT_FOUND_IN_DB"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_FILE = "INVALID_FILE"
    
    # ===== 新增：大模型相关错误码 =====
    LLM_API_ERROR = "LLM_API_ERROR"              # API调用失败
    LLM_TIMEOUT = "LLM_TIMEOUT"                  # 请求超时
    LLM_PARSE_ERROR = "LLM_PARSE_ERROR"          # 响应解析失败
    LLM_QUOTA_EXCEEDED = "LLM_QUOTA_EXCEEDED"    # 配额超限
    LLM_INVALID_RESPONSE = "LLM_INVALID_RESPONSE"  # 响应格式无效
    LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"    # 大模型未配置
```

### 5.2 降级策略

```python
class FallbackStrategy:
    """降级策略"""
    
    @staticmethod
    def handle_llm_failure(
        error: Exception,
        image: np.ndarray,
        ocr_strategy: RecognitionStrategy
    ) -> Dict[str, Any]:
        """
        LLM失败时的降级处理
        
        1. 记录错误日志
        2. 尝试OCR降级
        3. 返回结果（标记降级）
        """
        logger.error(f"LLM recognition failed: {error}, falling back to OCR")
        
        try:
            ocr_result = ocr_strategy.recognize(image)
            ocr_result["method"] = "ocr"
            ocr_result["fallback"] = {
                "reason": "llm_failed",
                "error": str(error)
            }
            return ocr_result
        except Exception as e:
            logger.error(f"OCR fallback also failed: {e}")
            return {
                "success": False,
                "error_code": ErrorCode.INTERNAL_ERROR,
                "message": "Both LLM and OCR recognition failed"
            }
```

### 5.3 重试机制

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class DoubaoEngine:
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _call_api_with_retry(self, image_base64: str) -> str:
        """带重试的API调用"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[...],
                timeout=self.timeout
            )
            return response.choices[0].message.content
        except Timeout:
            raise TimeoutError("Doubao API timeout")
        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise
```

---

## 六、性能优化

### 6.1 并发控制

```python
from asyncio import Semaphore

class LLMRateLimiter:
    """大模型并发限制器"""
    
    def __init__(self, max_concurrent: int = 3):
        self.semaphore = Semaphore(max_concurrent)
    
    async def acquire(self):
        """获取许可"""
        await self.semaphore.acquire()
    
    def release(self):
        """释放许可"""
        self.semaphore.release()
```

### 6.2 缓存机制（可选）

```python
import hashlib
from functools import lru_cache

class LLMCache:
    """大模型结果缓存"""
    
    def __init__(self, enabled: bool = False, ttl: int = 3600):
        self.enabled = enabled
        self.ttl = ttl
        self.cache = {}
    
    def get_image_hash(self, image: np.ndarray) -> str:
        """计算图片哈希"""
        return hashlib.md5(image.tobytes()).hexdigest()
    
    def get(self, image_hash: str) -> Optional[Dict]:
        """获取缓存结果"""
        if not self.enabled:
            return None
        # 实现缓存逻辑
    
    def set(self, image_hash: str, result: Dict):
        """设置缓存"""
        if self.enabled:
            # 实现缓存逻辑
            pass
```

### 6.3 监控指标

```python
class LLMMetrics:
    """大模型监控指标"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_latency = 0.0
        self.fallback_count = 0
    
    def record_request(self, success: bool, latency: float, fallback: bool):
        """记录请求"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.total_latency += latency
        if fallback:
            self.fallback_count += 1
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_requests": self.total_requests,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            "avg_latency": self.total_latency / self.total_requests if self.total_requests > 0 else 0,
            "fallback_rate": self.fallback_count / self.total_requests if self.total_requests > 0 else 0
        }
```

---

## 七、前端设计

### 7.1 UI组件

```html
<!-- 识别方式选择器 -->
<div class="method-selector">
    <h3>选择识别方式</h3>
    <div class="radio-group">
        <label class="radio-card">
            <input type="radio" name="method" value="ocr" checked>
            <div class="card-content">
                <div class="card-icon">⚡</div>
                <div class="card-title">OCR识别</div>
                <div class="card-desc">快速识别，适合清晰图像</div>
                <div class="card-tag">推荐</div>
            </div>
        </label>
        
        <label class="radio-card">
            <input type="radio" name="method" value="llm">
            <div class="card-content">
                <div class="card-icon">🤖</div>
                <div class="card-title">大模型识别</div>
                <div class="card-desc">智能识别，适合复杂场景</div>
                <div class="card-tag">高精度</div>
            </div>
        </label>
        
        <label class="radio-card">
            <input type="radio" name="method" value="auto">
            <div class="card-content">
                <div class="card-icon">🎯</div>
                <div class="card-title">智能切换</div>
                <div class="card-desc">自动选择最佳识别方式</div>
                <div class="card-tag">最佳</div>
            </div>
        </label>
    </div>
</div>
```

### 7.2 JavaScript逻辑

```javascript
// 提交识别请求
async function submitRecognition() {
    const formData = new FormData();
    const fileInput = document.getElementById('fileInput');
    const methodRadios = document.getElementsByName('method');
    
    // 获取选中的识别方式
    let method = 'ocr';
    for (const radio of methodRadios) {
        if (radio.checked) {
            method = radio.value;
            break;
        }
    }
    
    formData.append('file', fileInput.files[0]);
    
    // 显示加载状态
    showLoading(method);
    
    try {
        const response = await fetch(
            `/api/spec-locate?method=${method}`,
            {
                method: 'POST',
                body: formData
            }
        );
        
        const result = await response.json();
        displayResult(result);
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

// 显示加载状态（根据识别方式显示不同提示）
function showLoading(method) {
    const messages = {
        'ocr': '正在快速识别中...',
        'llm': '大模型分析中，请稍候...',
        'auto': '智能识别中...'
    };
    // 显示加载动画和提示
}
```

---

## 八、测试计划

### 8.1 单元测试

```python
# tests/test_doubao_engine.py
class TestDoubaoEngine:
    
    def test_image_to_base64(self):
        """测试图片Base64编码"""
        
    def test_response_parsing(self):
        """测试响应解析"""
        # 测试标准JSON格式
        # 测试Markdown包裹格式
        # 测试自然语言格式
        # 测试错误格式
        
    def test_api_call_with_mock(self):
        """测试API调用（使用Mock）"""
        
    def test_retry_mechanism(self):
        """测试重试机制"""

# tests/test_recognition_strategy.py
class TestRecognitionStrategy:
    
    def test_ocr_strategy(self):
        """测试OCR策略"""
        
    def test_llm_strategy(self):
        """测试LLM策略"""
        
    def test_hybrid_strategy(self):
        """测试混合策略"""
```

### 8.2 集成测试

```python
# tests/integration/test_pipeline.py
class TestPipelineIntegration:
    
    def test_ocr_mode_e2e(self):
        """测试OCR模式端到端流程"""
        
    def test_llm_mode_e2e(self):
        """测试LLM模式端到端流程"""
        
    def test_auto_mode_e2e(self):
        """测试Auto模式端到端流程"""
        
    def test_fallback_mechanism(self):
        """测试降级机制"""
```

### 8.3 性能测试

```python
# tests/performance/test_latency.py
class TestPerformance:
    
    def test_ocr_latency(self):
        """测试OCR延迟"""
        # 目标: < 1秒
        
    def test_llm_latency(self):
        """测试LLM延迟"""
        # 目标: < 5秒
        
    def test_concurrent_requests(self):
        """测试并发请求"""
        # 测试10个并发请求
```

### 8.4 准确率测试

准备测试集：
- **清晰图片**（30张）：OCR优势场景
- **模糊图片**（20张）：LLM优势场景
- **倾斜图片**（15张）：LLM优势场景
- **复杂背景**（15张）：LLM优势场景
- **边界情况**（20张）：多个规范号、特殊字符等

测试指标：
- 准确率（Accuracy）
- 召回率（Recall）
- F1分数
- 平均置信度

---

## 九、部署方案

### 9.1 环境要求

- Python 3.8+
- 依赖包：
  - volcenginesdkarkruntime（豆包SDK）
  - tenacity（重试机制）
  - 其他现有依赖

### 9.2 配置步骤

1. **安装依赖**
   ```bash
   pip install volcenginesdkarkruntime tenacity
   ```

2. **配置环境变量**
   ```bash
   # .env 文件
   DOUBAO_API_KEY=your_api_key_here
   LLM_ENABLED=true
   LLM_MODEL=doubao-vision-pro
   ```

3. **启动服务**
   ```bash
   uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002
   ```

### 9.3 监控与日志

- **日志级别**：INFO（生产）/ DEBUG（开发）
- **日志内容**：
  - 识别方式选择
  - API调用时间
  - 识别结果和置信度
  - 降级事件
  - 错误和异常

---

## 十、风险评估与应对

| 风险类型 | 风险描述 | 影响程度 | 应对方案 |
|---------|---------|---------|---------|
| API稳定性 | 豆包API可能不稳定 | 中 | 实现重试+降级机制 |
| 成本超预算 | 调用量过大导致成本高 | 中 | 默认OCR，按需LLM；设置配额告警 |
| 响应延迟 | LLM响应较慢（2-5秒） | 低 | 前端显示进度；设置超时保护 |
| 准确率不达标 | Prompt设计不佳 | 中 | 充分测试；Prompt迭代优化 |
| 并发限制 | API并发限制 | 低 | 实现并发控制；排队机制 |
| 配置错误 | 用户配置API密钥错误 | 低 | 启动时验证配置；友好错误提示 |

---

## 十一、后续优化方向

### 短期（1-3个月）
1. **Prompt优化**：根据实际使用反馈优化Prompt
2. **准确率提升**：收集badcase，针对性改进
3. **成本优化**：实现结果缓存，减少重复调用

### 中期（3-6个月）
1. **智能路由**：根据图片特征自动选择识别方式
2. **结果融合**：同时调用OCR和LLM，融合结果
3. **用户反馈**：收集用户修正，用于模型优化

### 长期（6-12个月）
1. **本地模型**：部署开源视觉大模型（如Qwen-VL）
2. **微调模型**：基于建筑规范领域数据微调
3. **多模态融合**：结合图像、文本、布局等多维度信息

---

## 十二、附录

### 附录A：豆包API文档参考
- 官方文档：https://www.volcengine.com/docs/82379/1298454
- 视觉模型：doubao-vision-pro, doubao-vision-lite
- 定价：根据token计费

### 附录B：依赖包版本
```
volcenginesdkarkruntime>=1.0.0
tenacity>=8.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
numpy>=1.24.0
opencv-python>=4.8.0
```

### 附录C：术语表
- **OCR**: Optical Character Recognition，光学字符识别
- **LLM**: Large Language Model，大语言模型
- **Vision Model**: 视觉大模型，支持图像理解
- **Prompt Engineering**: 提示词工程，优化模型输入
- **Fallback**: 降级，主方案失败时的备用方案

---

**文档变更历史**：
- v1.0 (2026-01-28): 初始版本，完整设计方案
