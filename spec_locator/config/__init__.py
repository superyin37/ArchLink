"""
配置模块初始化
"""

from spec_locator.config.config import (
    ErrorCode,
    ERROR_MESSAGES,
    SPEC_CODE_PATTERN,
    PAGE_PREFIX_PATTERN,
    PAGE_SUFFIX_PATTERN,
    OCRConfig,
    PreprocessConfig,
    GeometryConfig,
    ConfidenceConfig,
    APIConfig,
    PathConfig,
    LOG_LEVEL,
    LLMConfig,  # 新增
)

__all__ = [
    "ErrorCode",
    "ERROR_MESSAGES",
    "SPEC_CODE_PATTERN",
    "PAGE_PREFIX_PATTERN",
    "PAGE_SUFFIX_PATTERN",
    "OCRConfig",
    "PreprocessConfig",
    "GeometryConfig",
    "ConfidenceConfig",
    "APIConfig",
    "PathConfig",
    "LOG_LEVEL",
    "LLMConfig",  # 新增
]
