"""
规范编号识别与解析模块
- 从 OCR 文本识别规范编号
- 基于正则规则与字符修正
"""

import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

from spec_locator.config import SPEC_CODE_PATTERN
from spec_locator.ocr.ocr_engine import TextBox

logger = logging.getLogger(__name__)


@dataclass
class SpecCode:
    """规范编号数据"""
    code: str  # 规范编号（如 12J2）
    confidence: float  # 置信度
    source_text: str  # 原始识别文本
    source_idx: int  # 源文本框索引


class SpecCodeParser:
    """规范编号解析器"""

    # 常见的规范编号前缀数字
    VALID_PREFIXES = {
        "04", "05", "06", "07", "08", "09",
        "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25",
    }

    # 常见的规范编号字母
    VALID_LETTERS = {"J", "G", "C", "D", "T", "Z", "S"}

    # 字符修正规则（常见的 OCR 错误）
    CHAR_CORRECTIONS = {
        "0": "O",  # 数字0与字母O混淆
        "1": "I",  # 数字1与字母I混淆
        "5": "S",  # 数字5与字母S混淆
        "8": "B",  # 数字8与字母B混淆
    }

    def parse(self, text_boxes: List[TextBox]) -> List[SpecCode]:
        """
        从文本框列表中识别规范编号

        Args:
            text_boxes: OCR 识别的文本框列表

        Returns:
            规范编号列表
        """
        spec_codes = []

        for idx, box in enumerate(text_boxes):
            # 尝试从当前文本框识别
            code = self._extract_spec_code(box.text)
            if code:
                spec_codes.append(
                    SpecCode(
                        code=code,
                        confidence=box.confidence,
                        source_text=box.text,
                        source_idx=idx,
                    )
                )

        # 去重：保留置信度最高的
        spec_codes = self._deduplicate(spec_codes)

        logger.info(f"Parsed {len(spec_codes)} spec codes")
        return spec_codes

    def _extract_spec_code(self, text: str) -> Optional[str]:
        """
        从文本中提取规范编号

        Args:
            text: 输入文本

        Returns:
            规范编号或 None
        """
        text = text.strip()
        logger.debug(f"Extracting spec code from text: '{text}'")

        # 1. 尝试正则匹配
        match = re.search(SPEC_CODE_PATTERN, text)
        if match:
            code = match.group(1)
            # 清理匹配到的代码中的空格
            code = re.sub(r'\s+', '', code)
            logger.debug(f"Regex matched: '{code}'")
            # 验证规范编号有效性
            if self._validate_spec_code(code):
                logger.debug(f"Validated spec code: '{code}'")
                return code
            else:
                logger.debug(f"Failed validation: '{code}'")

        # 2. 尝试部分匹配与修正
        logger.debug(f"Trying correction for: '{text}'")
        code = self._correct_and_validate(text)
        if code:
            logger.debug(f"Corrected spec code: '{code}'")
            return code

        logger.debug(f"No spec code found in: '{text}'")
        return None

    def _validate_spec_code(self, code: str) -> bool:
        """
        验证规范编号的有效性

        Args:
            code: 规范编号

        Returns:
            是否有效
        """
        # 长度检查
        if len(code) < 4 or len(code) > 15:
            logger.debug(f"Length check failed for '{code}' (len={len(code)})")
            return False

        # 前缀检查（前2-3位数字）
        prefix_match = re.match(r"(\d{2,3})", code)
        if not prefix_match:
            logger.debug(f"No numeric prefix found in '{code}'")
            return False

        prefix = prefix_match.group(1)
        if prefix not in self.VALID_PREFIXES:
            logger.debug(f"Invalid prefix '{prefix}' in '{code}'")
            return False

        # 字母检查（数字后至少有一个字母）
        if not re.search(r"[A-Z]", code):
            logger.debug(f"No uppercase letter found in '{code}'")
            return False

        logger.debug(f"Validation passed for '{code}'")
        return True

    def _correct_and_validate(self, text: str) -> Optional[str]:
        """
        尝试修正常见的 OCR 错误

        Args:
            text: 输入文本

        Returns:
            修正后的规范编号或 None
        """
        # 移除常见的符号干扰（包括空格）
        cleaned = re.sub(r"[\\-_·. \s]", "", text)
        logger.debug(f"Cleaned text: '{text}' -> '{cleaned}'")

        # 尝试修正字符
        corrected = self._auto_correct_chars(cleaned)
        logger.debug(f"Corrected text: '{cleaned}' -> '{corrected}'")

        if self._validate_spec_code(corrected):
            return corrected

        return None

    def _auto_correct_chars(self, text: str) -> str:
        """自动修正常见的字符错误"""
        result = []
        for char in text:
            # 如果是容易混淆的字符，尝试修正
            if char in self.CHAR_CORRECTIONS:
                result.append(self.CHAR_CORRECTIONS[char])
            else:
                result.append(char)
        return "".join(result)

    def _deduplicate(self, spec_codes: List[SpecCode]) -> List[SpecCode]:
        """
        去重规范编号，保留置信度最高的

        Args:
            spec_codes: 规范编号列表

        Returns:
            去重后的列表
        """
        code_dict = {}
        for spec_code in spec_codes:
            key = spec_code.code
            if key not in code_dict or spec_code.confidence > code_dict[key].confidence:
                code_dict[key] = spec_code

        return list(code_dict.values())
