"""
页码识别与空间组合模块
- 识别页码的组成部分
- 结合空间关系进行页码组合
"""

import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

from spec_locator.config import PAGE_PREFIX_PATTERN, PAGE_SUFFIX_PATTERN
from spec_locator.ocr.ocr_engine import TextBox
from spec_locator.parser.geometry import GeometryCalculator

logger = logging.getLogger(__name__)


@dataclass
class PageCode:
    """页码数据"""
    page: str  # 完整页码（如 C11-2）
    confidence: float  # 置信度
    source_indices: List[int]  # 源文本框索引列表


@dataclass
class PagePart:
    """页码部分（前缀或后缀）"""
    text: str  # 文本
    part_type: str  # 'prefix' 或 'suffix'
    confidence: float  # 置信度
    source_idx: int  # 源文本框索引


class PageCodeParser:
    """页码解析器"""

    def __init__(self, max_distance: int = 100):
        """
        初始化

        Args:
            max_distance: 最大搜索距离
        """
        self.geometry = GeometryCalculator(max_distance=max_distance)

    def parse(self, text_boxes: List[TextBox]) -> List[PageCode]:
        """
        从文本框列表中识别页码

        Args:
            text_boxes: OCR 识别的文本框列表

        Returns:
            页码列表
        """
        # 1. 提取页码部分（前缀和后缀）
        page_parts = self._extract_page_parts(text_boxes)

        if not page_parts:
            logger.warning("No page parts found")
            return []

        # 2. 组合页码前缀和后缀
        page_codes = self._combine_page_parts(page_parts, text_boxes)

        logger.info(f"Parsed {len(page_codes)} page codes")
        return page_codes

    def _extract_page_parts(self, text_boxes: List[TextBox]) -> List[PagePart]:
        """
        提取页码的前缀和后缀部分

        Args:
            text_boxes: 文本框列表

        Returns:
            页码部分列表
        """
        page_parts = []

        for idx, box in enumerate(text_boxes):
            text = box.text.strip()

            # 检查是否为前缀（如 C11, P25）
            prefix_match = re.match(PAGE_PREFIX_PATTERN, text)
            if prefix_match:
                page_parts.append(
                    PagePart(
                        text=text,
                        part_type="prefix",
                        confidence=box.confidence,
                        source_idx=idx,
                    )
                )
                continue

            # 检查是否为纯数字后缀（如 2, 3）
            # 单独的 1-2 位数字，且相信度较高
            if re.match(r"^\\d{1,2}$", text) and box.confidence > 0.7:
                page_parts.append(
                    PagePart(
                        text=text,
                        part_type="suffix",
                        confidence=box.confidence,
                        source_idx=idx,
                    )
                )

        return page_parts

    def _combine_page_parts(
        self, page_parts: List[PagePart], text_boxes: List[TextBox]
    ) -> List[PageCode]:
        """
        组合页码前缀和后缀

        Args:
            page_parts: 页码部分列表
            text_boxes: 原始文本框列表

        Returns:
            完整的页码列表
        """
        page_codes = []

        for prefix in page_parts:
            if prefix.part_type != "prefix":
                continue

            # 在后缀中查找最近的（通常在右侧或下方）
            prefix_box = text_boxes[prefix.source_idx]
            candidates = []

            for suffix in page_parts:
                if suffix.part_type != "suffix":
                    continue

                suffix_box = text_boxes[suffix.source_idx]

                # 检查是否相邻（前缀和后缀应该距离较近）
                if self.geometry.is_neighbor(prefix_box, suffix_box, max_distance=150):
                    direction = self.geometry.get_direction(prefix_box, suffix_box)

                    # 通常后缀在前缀的右侧或下方
                    if direction in ["right", "below", "diag_br"]:
                        distance = self.geometry.calculate_distance(prefix_box, suffix_box)
                        candidates.append(
                            (suffix, distance, direction)
                        )

            # 选择距离最近的后缀
            if candidates:
                best_suffix, _, _ = min(candidates, key=lambda x: x[1])
                combined_page = f"{prefix.text}-{best_suffix.text}"
                combined_confidence = (
                    prefix.confidence + best_suffix.confidence
                ) / 2
                page_codes.append(
                    PageCode(
                        page=combined_page,
                        confidence=combined_confidence,
                        source_indices=[prefix.source_idx, best_suffix.source_idx],
                    )
                )
            else:
                # 如果没有找到后缀，仅返回前缀
                page_codes.append(
                    PageCode(
                        page=prefix.text,
                        confidence=prefix.confidence,
                        source_indices=[prefix.source_idx],
                    )
                )

        # 去重与排序
        page_codes = self._deduplicate_pages(page_codes)
        return page_codes

    def _deduplicate_pages(self, page_codes: List[PageCode]) -> List[PageCode]:
        """去重页码，保留置信度最高的"""
        page_dict = {}
        for page_code in page_codes:
            key = page_code.page
            if key not in page_dict or page_code.confidence > page_dict[key].confidence:
                page_dict[key] = page_code

        return list(page_dict.values())
