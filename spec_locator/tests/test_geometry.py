"""
单元测试 - 几何关系计算
"""

import pytest
import math
from spec_locator.ocr.ocr_engine import TextBox
from spec_locator.parser.geometry import GeometryCalculator


class TestGeometryCalculator:
    """几何关系计算器测试"""

    @pytest.fixture
    def calculator(self):
        return GeometryCalculator(max_distance=100)

    @pytest.fixture
    def sample_boxes(self):
        """创建示例文本框"""
        box1 = TextBox(
            text="12J2",
            confidence=0.95,
            bbox=((10, 10), (50, 10), (50, 30), (10, 30))
        )
        box2 = TextBox(
            text="C11",
            confidence=0.90,
            bbox=((60, 10), (90, 10), (90, 30), (60, 30))
        )
        box3 = TextBox(
            text="2",
            confidence=0.85,
            bbox=((100, 10), (110, 10), (110, 30), (100, 30))
        )
        return [box1, box2, box3]

    def test_calculate_distance(self, calculator, sample_boxes):
        """测试距离计算"""
        box1 = sample_boxes[0]
        box2 = sample_boxes[1]
        distance = calculator.calculate_distance(box1, box2)
        
        # box1 中心: (30, 20), box2 中心: (75, 20)
        expected = 45
        assert abs(distance - expected) < 1

    def test_calculate_gaps(self, calculator, sample_boxes):
        """测试间距计算"""
        box1 = sample_boxes[0]
        box2 = sample_boxes[1]
        h_gap, v_gap = calculator.calculate_gaps(box1, box2)
        
        # 水平间距: 60 - 50 = 10
        # 竖直间距: 应该没有重叠
        assert h_gap == 10

    def test_get_direction(self, calculator, sample_boxes):
        """测试方向判定"""
        box1 = sample_boxes[0]
        box2 = sample_boxes[1]
        direction = calculator.get_direction(box1, box2)
        
        # box2 在 box1 右侧
        assert direction == "right"

    def test_is_neighbor(self, calculator, sample_boxes):
        """测试邻接判定"""
        box1 = sample_boxes[0]
        box2 = sample_boxes[1]
        
        assert calculator.is_neighbor(box1, box2, max_distance=100) is True
        assert calculator.is_neighbor(box1, box2, max_distance=30) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
