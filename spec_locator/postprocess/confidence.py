"""
后处理与置信度评估模块
- 汇总多个候选结果
- 计算整体置信度
- 对候选结果进行排序
"""

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
from spec_locator.config import ConfidenceConfig

from spec_locator.parser.spec_code import SpecCode
from spec_locator.parser.page_code import PageCode

logger = logging.getLogger(__name__)


@dataclass
class SpecMatch:
    """规范与页码的匹配结果"""
    spec_code: str
    page_code: str
    confidence: float
    spec_confidence: float
    page_confidence: float


class ConfidenceEvaluator:
    """置信度评估器"""

    def __init__(self, config: ConfidenceConfig = None):
        """
        初始化

        Args:
            config: 置信度配置
        """
        self.config = config or ConfidenceConfig()

    def evaluate(
        self, spec_codes: List[SpecCode], page_codes: List[PageCode]
    ) -> List[SpecMatch]:
        """
        评估规范编号和页码的配对匹配

        Args:
            spec_codes: 识别到的规范编号列表
            page_codes: 识别到的页码列表

        Returns:
            排序后的匹配结果列表
        """
        if not spec_codes or not page_codes:
            logger.warning(f"Empty input: specs={len(spec_codes)}, pages={len(page_codes)}")
            return []

        matches = []

        # 生成所有可能的配对
        for spec in spec_codes:
            for page in page_codes:
                confidence = self._calculate_confidence(spec, page)

                # 过滤低置信度结果
                if confidence >= self.config.MIN_CONFIDENCE:
                    matches.append(
                        SpecMatch(
                            spec_code=spec.code,
                            page_code=page.page,
                            confidence=confidence,
                            spec_confidence=spec.confidence,
                            page_confidence=page.confidence,
                        )
                    )

        # 按置信度排序
        matches.sort(key=lambda m: m.confidence, reverse=True)

        logger.info(f"Generated {len(matches)} candidate matches")
        return matches

    def _calculate_confidence(self, spec: SpecCode, page: PageCode) -> float:
        """
        计算规范和页码的置信度

        Args:
            spec: 规范编号
            page: 页码

        Returns:
            综合置信度（0-1）
        """
        # 1. OCR置信度：取平均值后应用权重
        ocr_score = (spec.confidence + page.confidence) / 2 * self.config.OCR_WEIGHT
        
        # 2. 几何关系得分（简化版：来自相邻文本框）
        geometry_score = self._get_geometry_score(spec, page) * self.config.GEOMETRY_WEIGHT
        
        # 3. 模式匹配奖励
        pattern_score = self._get_pattern_bonus(spec, page)

        total_confidence = ocr_score + geometry_score + pattern_score
        
        logger.debug(
            f"Confidence breakdown for {spec.code}+{page.page}: "
            f"OCR={ocr_score:.3f}, Geometry={geometry_score:.3f}, "
            f"Pattern={pattern_score:.3f}, Total={total_confidence:.3f}"
        )
        
        return min(total_confidence, 1.0)
    
    def _get_geometry_score(self, spec: SpecCode, page: PageCode) -> float:
        """
        计算几何关系得分（简化版）
        
        Args:
            spec: 规范编号
            page: 页码
            
        Returns:
            几何得分（0-1）
        """
        # 简化判断：如果页码的source_indices包含相邻索引，给高分
        spec_idx = spec.source_idx
        page_indices = page.source_indices
        
        # 检查是否在附近（差距<=2）
        for page_idx in page_indices:
            if abs(page_idx - spec_idx) <= 2:
                return 1.0  # 相邻，高分
        
        # 不相邻，低分
        return 0.3

    def _get_pattern_bonus(self, spec: SpecCode, page: PageCode) -> float:
        """
        根据模式匹配给予奖励

        Args:
            spec: 规范编号
            page: 页码

        Returns:
            奖励值（0-pattern_weight）
        """
        bonus = 0.0

        # 规范编号和页码来自相邻的文本框时给予奖励
        spec_indices = {spec.source_idx}
        page_indices = set(page.source_indices)

        overlap = spec_indices & page_indices
        if overlap:
            # 来自同一文本框（较少见，但可能）
            bonus += self.config.PATTERN_WEIGHT * 0.5

        # 页码格式正确（如 C11-2）给予奖励
        if "-" in page.page:
            bonus += self.config.PATTERN_WEIGHT * 0.3

        return min(bonus, self.config.PATTERN_WEIGHT)


class ResultFilter:
    """结果过滤器"""

    @staticmethod
    def get_top_n(matches: List[SpecMatch], n: int = 5) -> List[SpecMatch]:
        """
        获取前 N 个最佳匹配

        Args:
            matches: 所有匹配
            n: 返回数量

        Returns:
            前 N 个匹配
        """
        return matches[:n]

    @staticmethod
    def get_best_match(matches: List[SpecMatch]) -> Optional[SpecMatch]:
        """
        获取最佳匹配

        Args:
            matches: 所有匹配

        Returns:
            最佳匹配或 None
        """
        return matches[0] if matches else None

    @staticmethod
    def filter_by_confidence(
        matches: List[SpecMatch], min_confidence: float
    ) -> List[SpecMatch]:
        """
        按置信度过滤

        Args:
            matches: 所有匹配
            min_confidence: 最小置信度

        Returns:
            过滤后的匹配列表
        """
        return [m for m in matches if m.confidence >= min_confidence]
