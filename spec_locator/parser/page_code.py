"""
页码识别模块（终版：子串 Anchor + 上下结构解析）
"""

import re
import logging
from typing import List, Tuple
from dataclasses import dataclass

from spec_locator.ocr.ocr_engine import TextBox
from spec_locator.parser.geometry import GeometryCalculator

logger = logging.getLogger(__name__)


# ======================================================
# Data Structures
# ======================================================

@dataclass
class PageCode:
    page: str
    confidence: float
    source_indices: List[int]


@dataclass
class PageCandidate:
    text: str
    confidence: float
    source_idx: int
    distance: float
    score: float
    center: Tuple[float, float]


# ======================================================
# Utils
# ======================================================

def normalize_text(text: str) -> str:
    """统一文本格式"""
    return re.sub(r"\s+", "", text).upper()


def deduplicate_pages(pages: List[PageCode]) -> List[PageCode]:
    """去重页码，保留最高置信度"""
    table = {}

    for p in pages:
        key = p.page.upper()
        if key not in table or p.confidence > table[key].confidence:
            table[key] = p

    return list(table.values())


# ======================================================
# Anchor-based Extractor
# ======================================================

class PageByAnchorExtractor:
    """
    基于规范号锚点的页码提取器（子串匹配版）
    """

    # 子串规范号匹配（核心）
    ANCHOR_PATTERN = re.compile(
        r'(?<!\d)([A-Z]{0,2}\d{2,3}[A-Z]+\d{1,4}(?:-\d+)?)(?!\d)',
        re.IGNORECASE
    )

    # 页码格式
    PAGE_PATTERN = re.compile(r'^[A-Z]?\d+$', re.IGNORECASE)

    MAX_DIGITS = 3   # 防止 1200 / 2000

    def __init__(
        self,
        radius: int = 300,
        x_thresh: int = 18,
        y_thresh: int = 25,
        conf_min: float = 0.5,
        eps: float = 1e-6,
    ):
        self.radius = radius
        self.x_thresh = x_thresh
        self.y_thresh = y_thresh
        self.conf_min = conf_min
        self.eps = eps

        self.geometry = GeometryCalculator(max_distance=radius)

    # --------------------------------------------------
    # Main
    # --------------------------------------------------

    def extract(self, boxes: List[TextBox]) -> List[PageCode]:

        anchors = self._find_anchors(boxes)

        if not anchors:
            logger.warning("No anchor found")
            return []

        results: List[PageCode] = []

        for anchor_idx, anchor_box, spec in anchors:

            candidates = self._find_candidates(
                anchor_idx, anchor_box, boxes
            )

            if not candidates:
                continue

            # 按 score 排序（关键）
            candidates.sort(key=lambda c: c.score, reverse=True)

            top = candidates[:2]

            # 上下圆结构判断
            if len(top) == 2 and self._is_vertical_pair(top[0], top[1]):
                chosen = max(top, key=lambda c: c.center[1])
            else:
                chosen = top[0]

            results.append(
                PageCode(
                    page=chosen.text,
                    confidence=chosen.score,
                    source_indices=[chosen.source_idx],
                )
            )

        results = deduplicate_pages(results)

        logger.info(f"Anchor parser: {len(results)} pages")

        return results

    # --------------------------------------------------
    # Anchor Detection
    # --------------------------------------------------

    def _find_anchors(self, boxes):

        anchors = []

        for idx, box in enumerate(boxes):

            text = normalize_text(box.text)
            m = self.ANCHOR_PATTERN.search(text)

            if m:
                print(f"Found anchor '{m.group(1)}' in box '{text}'")
                spec = m.group(1).upper()
                anchors.append((idx, box, spec))

        return anchors

    # --------------------------------------------------
    # Candidate Search
    # --------------------------------------------------

    def _find_candidates(
        self,
        anchor_idx: int,
        anchor_box: TextBox,
        boxes: List[TextBox],
    ) -> List[PageCandidate]:

        candidates = []

        for idx, box in enumerate(boxes):
            
            if idx == anchor_idx:
                continue

            text = normalize_text(box.text)
            distance = self.geometry.calculate_distance(
                anchor_box, box
            )
            print("dist:", distance, "radius:", self.radius, "text:", text)
            if not text:
                continue

            # 页码过滤
            if not self.PAGE_PATTERN.match(text):
                continue

            # 防止规范号混入
            if self.ANCHOR_PATTERN.search(text):
                continue

            # 防止尺寸干扰
            if text.isdigit() and len(text) > self.MAX_DIGITS:
                continue

            if box.confidence < self.conf_min:
                continue

            

            if distance > self.radius:
                continue

            score = box.confidence / (distance + self.eps)
            print(f"  Candidate '{text}' (conf: {box.confidence:.2f}, dist: {distance:.1f}, score: {score:.4f})")
            candidates.append(
                PageCandidate(
                    text=text,
                    confidence=box.confidence,
                    source_idx=idx,
                    distance=distance,
                    score=score,
                    center=box.get_center(),
                )
            )
        return candidates

    # --------------------------------------------------
    # Layout Analysis
    # --------------------------------------------------

    def _is_vertical_pair(self, a: PageCandidate, b: PageCandidate) -> bool:

        return (
            abs(a.center[0] - b.center[0]) < self.x_thresh
            and abs(a.center[1] - b.center[1]) > self.y_thresh
        )


# ======================================================
# Fallback Parser
# ======================================================

class LegacyPageParser:
    """
    安全兜底解析器（仅识别最基本页码）
    """

    PAGE_PATTERN = re.compile(r'^[A-Z]?\d+$', re.IGNORECASE)

    def parse(self, boxes: List[TextBox]) -> List[PageCode]:

        results = []

        for idx, box in enumerate(boxes):

            text = normalize_text(box.text)

            if not self.PAGE_PATTERN.match(text):
                continue

            if box.confidence < 0.6:
                continue

            results.append(
                PageCode(
                    page=text,
                    confidence=box.confidence,
                    source_indices=[idx],
                )
            )

        return deduplicate_pages(results)


# ======================================================
# Unified Interface
# ======================================================

class PageCodeParser:
    """
    页码解析统一接口（Anchor → Fallback）
    """

    def __init__(self, max_distance: int = 300):

        self.anchor_parser = PageByAnchorExtractor(
            radius=max_distance
        )

        self.legacy_parser = LegacyPageParser()

    def parse(self, boxes: List[TextBox]) -> List[PageCode]:

        # 主策略
        pages = self.anchor_parser.extract(boxes)

        if pages:
            return pages

        logger.warning("Fallback to legacy parser")

        # 兜底
        return self.legacy_parser.parse(boxes)
