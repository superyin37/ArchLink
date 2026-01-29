"""
几何关系计算模块
- 文本框距离计算
- 方向与邻近关系判定
- 空间关系分析
"""

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass

from spec_locator.ocr.ocr_engine import TextBox


@dataclass
class GeometryRelation:
    """几何关系数据"""
    source_idx: int  # 源文本框索引
    target_idx: int  # 目标文本框索引
    distance: float  # 欧氏距离
    direction: str  # 方向（right, below, diag_br等）
    horizontal_gap: float  # 水平间距
    vertical_gap: float  # 竖直间距


class GeometryCalculator:
    """几何关系计算器"""

    def __init__(self, max_distance: int = 300, direction_tolerance: int = 30):
        """
        初始化

        Args:
            max_distance: 最大邻近距离（像素）
            direction_tolerance: 方向容差（度）
        """
        self.max_distance = max_distance
        self.direction_tolerance = direction_tolerance

    def calculate_distance(self, box1: TextBox, box2: TextBox) -> float:
        """计算两个文本框中心点的欧氏距离"""
        c1 = box1.get_center()
        c2 = box2.get_center()
        return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)

    def calculate_gaps(
        self, box1: TextBox, box2: TextBox
    ) -> Tuple[float, float]:
        """
        计算两个文本框之间的间距

        Returns:
            (水平间距, 竖直间距)
        """
        # box1 右边 到 box2 左边
        h_gap = min(p[0] for p in box2.bbox) - max(p[0] for p in box1.bbox)

        # box1 下边 到 box2 上边
        v_gap = min(p[1] for p in box2.bbox) - max(p[1] for p in box1.bbox)

        return (h_gap, v_gap)

    def get_direction(self, box1: TextBox, box2: TextBox) -> str:
        """
        判断 box2 相对于 box1 的方向

        Returns:
            'right' (右侧), 'below' (下方), 'diag_br' (右下), etc.
        """
        h_gap, v_gap = self.calculate_gaps(box1, box2)
        c1 = box1.get_center()
        c2 = box2.get_center()

        # 计算方向角
        dx = c2[0] - c1[0]
        dy = c2[1] - c1[1]
        angle = math.degrees(math.atan2(dy, dx))

        # 标准化角度到 0-360
        if angle < 0:
            angle += 360

        # 根据角度判断方向
        # 0°: 右, 90°: 下, 180°: 左, 270°: 上
        if angle < 45 or angle >= 315:
            return "right"
        elif 45 <= angle < 135:
            return "below"
        elif 135 <= angle < 225:
            return "left"
        elif 225 <= angle < 315:
            return "above"

    def is_neighbor(
        self, box1: TextBox, box2: TextBox, max_distance: Optional[int] = None
    ) -> bool:
        """判断两个文本框是否相邻"""
        if max_distance is None:
            max_distance = self.max_distance
        distance = self.calculate_distance(box1, box2)
        return distance <= max_distance

    def find_neighbors(
        self, boxes: List[TextBox], target_idx: int, max_distance: Optional[int] = None
    ) -> List[GeometryRelation]:
        """
        查找目标文本框的相邻文本框

        Args:
            boxes: 所有文本框
            target_idx: 目标文本框索引
            max_distance: 最大搜索距离

        Returns:
            几何关系列表
        """
        if max_distance is None:
            max_distance = self.max_distance

        neighbors = []
        target_box = boxes[target_idx]

        for i, box in enumerate(boxes):
            if i == target_idx:
                continue

            if self.is_neighbor(target_box, box, max_distance):
                h_gap, v_gap = self.calculate_gaps(target_box, box)
                direction = self.get_direction(target_box, box)

                relation = GeometryRelation(
                    source_idx=target_idx,
                    target_idx=i,
                    distance=self.calculate_distance(target_box, box),
                    direction=direction,
                    horizontal_gap=h_gap,
                    vertical_gap=v_gap,
                )
                neighbors.append(relation)

        # 按距离排序
        neighbors.sort(key=lambda r: r.distance)
        return neighbors

    def find_aligned(
        self, boxes: List[TextBox], reference_idx: int, direction: str = "right"
    ) -> List[int]:
        """
        查找与参考文本框对齐的文本框

        Args:
            boxes: 所有文本框
            reference_idx: 参考文本框索引
            direction: 对齐方向 ('right', 'below')

        Returns:
            对齐的文本框索引列表
        """
        aligned = []
        ref_box = boxes[reference_idx]
        ref_center = ref_box.get_center()

        tolerance = 15  # 像素容差

        for i, box in enumerate(boxes):
            if i == reference_idx:
                continue

            box_center = box.get_center()

            if direction == "right":
                # 水平对齐（Y 坐标接近）
                if abs(box_center[1] - ref_center[1]) < tolerance:
                    if box_center[0] > ref_center[0]:
                        aligned.append(i)

            elif direction == "below":
                # 竖直对齐（X 坐标接近）
                if abs(box_center[0] - ref_center[0]) < tolerance:
                    if box_center[1] > ref_center[1]:
                        aligned.append(i)

        aligned.sort(
            key=lambda i: boxes[i].get_center()[0 if direction == "right" else 1]
        )
        return aligned
