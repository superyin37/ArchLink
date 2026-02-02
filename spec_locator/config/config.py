"""
全局配置管理
"""

import os
from enum import Enum
from pathlib import Path

# 加载.env文件
try:
    from dotenv import load_dotenv
    # 查找.env文件：先查找spec_locator目录，再查找项目根目录
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # 尝试项目根目录
        env_file = Path(__file__).parent.parent.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
except ImportError:
    pass  # 如果没有安装python-dotenv，继续使用系统环境变量

# ===== 基础配置 =====
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ===== 错误码定义 =====
class ErrorCode(str, Enum):
    """错误码枚举"""
    NO_TEXT = "NO_TEXT"  # 未识别到有效文本
    NO_SPEC_CODE = "NO_SPEC_CODE"  # 未识别到规范编号
    NO_PAGE_CODE = "NO_PAGE_CODE"  # 未识别到页码
    NO_MATCH = "NO_MATCH"  # 无法组合有效结果
    FILE_NOT_FOUND_IN_DB = "FILE_NOT_FOUND_IN_DB"  # 识别成功但数据库中未找到文件
    INTERNAL_ERROR = "INTERNAL_ERROR"  # 内部错误
    INVALID_FILE = "INVALID_FILE"  # 无效文件
    
    # 大模型相关错误码（新增）
    LLM_API_ERROR = "LLM_API_ERROR"  # API调用失败
    LLM_TIMEOUT = "LLM_TIMEOUT"  # 请求超时
    LLM_PARSE_ERROR = "LLM_PARSE_ERROR"  # 响应解析失败
    LLM_QUOTA_EXCEEDED = "LLM_QUOTA_EXCEEDED"  # 配额超限
    LLM_INVALID_RESPONSE = "LLM_INVALID_RESPONSE"  # 响应格式无效
    LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"  # 大模型未配置


ERROR_MESSAGES = {
    ErrorCode.NO_TEXT: "未能从图像中识别到有效文本。请确保图片清晰，包含规范编号和页码信息。",
    ErrorCode.NO_SPEC_CODE: "未能识别到规范编号。请确保图像中包含规范编号（如：12J2、20G908-1等）。",
    ErrorCode.NO_PAGE_CODE: "未能识别到页码。请确保图像中包含页码信息（如：C11、C11-2等）。",
    ErrorCode.NO_MATCH: "无法将识别到的规范编号和页码进行有效组合。",
    ErrorCode.FILE_NOT_FOUND_IN_DB: "已识别到规范编号和页码，但数据库中未找到对应的规范文件。",
    ErrorCode.INTERNAL_ERROR: "服务器内部错误，请稍后重试。",
    ErrorCode.INVALID_FILE: "无效的文件格式。支持的格式：png、jpg、jpeg。",
    
    # 大模型相关错误消息
    ErrorCode.LLM_API_ERROR: "大模型API调用失败，请检查API密钥和网络连接。",
    ErrorCode.LLM_TIMEOUT: "大模型请求超时，请稍后重试。",
    ErrorCode.LLM_PARSE_ERROR: "无法解析大模型响应，请联系技术支持。",
    ErrorCode.LLM_QUOTA_EXCEEDED: "大模型API配额已用尽，请检查账户余额。",
    ErrorCode.LLM_INVALID_RESPONSE: "大模型返回无效响应，请重试。",
    ErrorCode.LLM_NOT_CONFIGURED: "大模型未配置或配置不完整。请设置LLM_PROVIDER和对应的API密钥。",
}

# 英文错误消息（用于日志）
ERROR_MESSAGES_EN = {
    ErrorCode.NO_TEXT: "Failed to recognize text in image.",
    ErrorCode.NO_SPEC_CODE: "Failed to identify spec code from image.",
    ErrorCode.NO_PAGE_CODE: "Failed to identify page code from image.",
    ErrorCode.NO_MATCH: "Failed to identify spec code or page from image.",
    ErrorCode.FILE_NOT_FOUND_IN_DB: "Spec code and page identified but file not found in database.",
    ErrorCode.INTERNAL_ERROR: "Internal server error.",
    ErrorCode.INVALID_FILE: "Invalid file format. Supported: png, jpg, jpeg.",
    
    # LLM related errors
    ErrorCode.LLM_API_ERROR: "LLM API call failed.",
    ErrorCode.LLM_TIMEOUT: "LLM request timeout.",
    ErrorCode.LLM_PARSE_ERROR: "Failed to parse LLM response.",
    ErrorCode.LLM_QUOTA_EXCEEDED: "LLM API quota exceeded.",
    ErrorCode.LLM_INVALID_RESPONSE: "LLM returned invalid response.",
    ErrorCode.LLM_NOT_CONFIGURED: "LLM is not configured. Please set LLM_PROVIDER and API key.",
}

# ===== 规范编号正则规则 =====
# 匹配如 12J2, 20G908-1, 23J908-8, L13J8, L13J5-1 等规范编号（允许空格）
# 支持可选的字母前缀（如 L、苏 等地方标准）
SPEC_CODE_PATTERN = r"([A-Z]{0,2}\d{2,3}\s*[A-Z]\s*\d{1,3}(?:-\d+)?)"

# ===== 页码正则规则 =====
# 匹配如 C11, C11-2, P23 等页码前缀
PAGE_PREFIX_PATTERN = r"([A-Z])(\d{1,3})"
# 匹配页码后缀
PAGE_SUFFIX_PATTERN = r"-(\d+)"

# ===== OCR 配置 =====
class OCRConfig:
    """OCR 引擎配置"""
    USE_GPU = os.getenv("OCR_USE_GPU", "false").lower() == "true"
    PRECISION = os.getenv("OCR_PRECISION", "fp32")  # fp32, fp16
    LANGUAGE = "ch"  # 中文识别
    CONF_THRESHOLD = float(os.getenv("OCR_CONF_THRESHOLD", 0.3))
    
    # 懒加载配置
    LAZY_LOAD = os.getenv("OCR_LAZY_LOAD", "true").lower() == "true"
    WARMUP_ON_STARTUP = os.getenv("OCR_WARMUP_ON_STARTUP", "false").lower() == "true"


# ===== 图像预处理配置 =====
class PreprocessConfig:
    """图像预处理配置"""
    MAX_IMAGE_SIZE = 4096  # 最大图像尺寸
    MIN_IMAGE_SIZE = 100   # 最小图像尺寸
    ENHANCE_CONTRAST = True  # 是否增强对比度
    REMOVE_LINES = True  # 是否去除结构线


# ===== 几何关系配置 =====
class GeometryConfig:
    """几何关系计算配置"""
    MAX_DISTANCE = 300  # 最大邻近距离（像素）
    DIRECTION_TOLERANCE = 30  # 方向容差（度）


# ===== 置信度配置 =====
class ConfidenceConfig:
    """置信度评估配置"""
    OCR_WEIGHT = 0.5  # OCR 置信度权重
    GEOMETRY_WEIGHT = 0.3  # 几何关系权重
    PATTERN_WEIGHT = 0.2  # 模式匹配权重
    MIN_CONFIDENCE = 0.1  # 最小置信度阈值


# ===== API 配置 =====
class APIConfig:
    """API 服务配置"""
    HOST = os.getenv("API_HOST", "0.0.0.0")
    PORT = int(os.getenv("API_PORT", 8000))
    WORKERS = int(os.getenv("API_WORKERS", 4))
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


# ===== 文件路径配置 =====
class PathConfig:
    """文件路径配置"""
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 数据目录 - 支持环境变量配置
    SPEC_DATA_DIR = os.getenv(
        "SPEC_DATA_DIR",
        os.path.join(os.path.dirname(PROJECT_ROOT), "output_pages")  # 默认 ../output_pages
    )
    
    # 其他目录（可通过环境变量配置）
    UPLOAD_DIR = os.getenv(
        "SPEC_UPLOAD_DIR",
        os.path.join(PROJECT_ROOT, "uploads")
    )
    TEMP_DIR = os.getenv(
        "SPEC_TEMP_DIR",
        os.path.join(PROJECT_ROOT, "temp")
    )
    LOG_DIR = os.getenv(
        "SPEC_LOG_DIR",
        os.path.join(PROJECT_ROOT, "logs")
    )

    @staticmethod
    def ensure_dirs():
        """确保必要目录存在"""
        for dir_path in [PathConfig.UPLOAD_DIR, PathConfig.TEMP_DIR, PathConfig.LOG_DIR]:
            os.makedirs(dir_path, exist_ok=True)
    
    @staticmethod
    def validate_data_dir():
        """验证数据目录是否存在且可访问"""
        if not os.path.exists(PathConfig.SPEC_DATA_DIR):
            raise FileNotFoundError(
                f"数据目录不存在: {PathConfig.SPEC_DATA_DIR}\n"
                f"请设置环境变量 SPEC_DATA_DIR 或创建默认目录"
            )
        if not os.path.isdir(PathConfig.SPEC_DATA_DIR):
            raise NotADirectoryError(
                f"SPEC_DATA_DIR 不是有效目录: {PathConfig.SPEC_DATA_DIR}"
            )


# ===== 大模型配置 =====
class LLMConfig:
    """大模型配置"""
    
    # 基础配置
    ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
    PROVIDER = os.getenv("LLM_PROVIDER", "doubao").lower()  # doubao/openai/gemini
    
    # API密钥配置（根据提供商自动选择）
    _API_KEYS = {
        "doubao": os.getenv("DOUBAO_API_KEY") or os.getenv("ARK_API_KEY"),
        "openai": os.getenv("OPENAI_API_KEY"),
        "gemini": os.getenv("GEMINI_API_KEY")
    }
    API_KEY = _API_KEYS.get(PROVIDER)
    
    # 模型配置（根据提供商设置默认值）
    _DEFAULT_MODELS = {
        "doubao": "doubao-vision-pro",
        "openai": "gpt-4o",
        "gemini": "gemini-1.5-pro"
    }
    MODEL = os.getenv("LLM_MODEL", _DEFAULT_MODELS.get(PROVIDER, "doubao-vision-pro"))
    
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
        import logging
        logger = logging.getLogger(__name__)
        
        if LLMConfig.ENABLED:
            if LLMConfig.PROVIDER not in ["doubao", "openai", "gemini"]:
                logger.warning(f"Unknown LLM_PROVIDER: {LLMConfig.PROVIDER}, falling back to 'doubao'")
                LLMConfig.PROVIDER = "doubao"
                LLMConfig.API_KEY = LLMConfig._API_KEYS.get("doubao")
            
            if not LLMConfig.API_KEY:
                logger.warning(f"LLM is enabled but API key for '{LLMConfig.PROVIDER}' is not set")
                return False
        
        return True
