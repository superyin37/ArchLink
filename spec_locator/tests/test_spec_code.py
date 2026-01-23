"""
单元测试 - 规范编号解析器
"""

import pytest
from spec_locator.parser.spec_code import SpecCodeParser


class TestSpecCodeParser:
    """规范编号解析器测试"""

    @pytest.fixture
    def parser(self):
        return SpecCodeParser()

    def test_extract_valid_spec_code(self, parser):
        """测试提取有效的规范编号"""
        assert parser._extract_spec_code("12J2") == "12J2"
        assert parser._extract_spec_code("20G908-1") == "20G908-1"
        assert parser._extract_spec_code("23J908-8") == "23J908-8"

    def test_extract_spec_code_with_noise(self, parser):
        """测试从含有噪声的文本中提取规范编号"""
        assert parser._extract_spec_code("《12J2》") == "12J2"
        assert parser._extract_spec_code("标准：20G908-1") == "20G908-1"

    def test_validate_spec_code(self, parser):
        """测试规范编号验证"""
        assert parser._validate_spec_code("12J2") is True
        assert parser._validate_spec_code("20G908-1") is True
        assert parser._validate_spec_code("99Z999-99") is True
        
        # 无效的编号
        assert parser._validate_spec_code("J2") is False  # 前缀不足
        assert parser._validate_spec_code("12345") is False  # 无字母
        assert parser._validate_spec_code("01J2") is False  # 前缀不在有效范围

    def test_correct_and_validate(self, parser):
        """测试字符修正"""
        # 测试数字与字母混淆
        code = parser._correct_and_validate("12J2")
        assert code == "12J2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
