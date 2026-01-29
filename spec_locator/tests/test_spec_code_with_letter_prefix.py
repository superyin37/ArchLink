"""
测试带字母前缀的规范号识别（如 L13J8, L13J5-1）
"""

import re
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spec_locator.config import SPEC_CODE_PATTERN
from spec_locator.parser.spec_code import SpecCodeParser
from spec_locator.ocr.ocr_engine import TextBox


def test_spec_code_pattern():
    """测试正则表达式是否能匹配带字母前缀的规范号"""
    
    print("=" * 60)
    print("测试 SPEC_CODE_PATTERN 正则表达式")
    print("=" * 60)
    
    test_cases = [
        ("L13J8", True, "地方标准 - 单字母前缀"),
        ("L13J5-1", True, "地方标准 - 单字母前缀带版本号"),
        ("苏J01-2005", True, "地方标准 - 双字母前缀"),
        ("12J2", True, "国家标准 - 无前缀"),
        ("20G908-1", True, "国家标准 - 带版本号"),
        ("23J908-8", True, "国家标准 - 带版本号"),
        ("06J908-1", True, "国家标准 - 06年系列"),
    ]
    
    pattern = re.compile(SPEC_CODE_PATTERN)
    
    for text, should_match, desc in test_cases:
        match = pattern.search(text)
        matched = match is not None
        
        status = "✅" if matched == should_match else "❌"
        result = match.group(1) if match else "未匹配"
        
        print(f"{status} {desc:30s} | 输入: {text:15s} | 结果: {result}")
    
    print()


def test_spec_code_parser():
    """测试 SpecCodeParser 是否能正确解析带字母前缀的规范号"""
    
    print("=" * 60)
    print("测试 SpecCodeParser 解析器")
    print("=" * 60)
    
    parser = SpecCodeParser()
    
    test_cases = [
        ("L13J8", "L13J8", "地方标准 - 单字母前缀"),
        ("L13J5-1", "L13J5-1", "地方标准 - 单字母前缀带版本号"),
        ("12J2", "12J2", "国家标准 - 无前缀"),
        ("20G908-1", "20G908-1", "国家标准 - 带版本号"),
    ]
    
    for text, expected, desc in test_cases:
        # 创建模拟的 TextBox
        text_boxes = [
            TextBox(
                text=text,
                confidence=0.95,
                bbox=[[0, 0], [100, 0], [100, 50], [0, 50]]
            )
        ]
        
        spec_codes = parser.parse(text_boxes)
        
        if spec_codes:
            result = spec_codes[0].code
            status = "✅" if result == expected else "❌"
            print(f"{status} {desc:30s} | 输入: {text:15s} | 识别: {result}")
        else:
            print(f"❌ {desc:30s} | 输入: {text:15s} | 识别: 失败")
    
    print()


def test_validation():
    """测试 _validate_spec_code 方法"""
    
    print("=" * 60)
    print("测试规范号验证逻辑")
    print("=" * 60)
    
    parser = SpecCodeParser()
    
    test_cases = [
        ("L13J8", True, "地方标准 - 单字母前缀"),
        ("L13J5-1", True, "地方标准 - 单字母前缀带版本号"),
        ("苏J01", False, "中文前缀（暂不支持）"),
        ("12J2", True, "国家标准 - 无前缀"),
        ("ABC123", False, "无效格式"),
        ("13J8", True, "有效的标准号"),
    ]
    
    for code, should_be_valid, desc in test_cases:
        is_valid = parser._validate_spec_code(code)
        status = "✅" if is_valid == should_be_valid else "❌"
        result = "有效" if is_valid else "无效"
        
        print(f"{status} {desc:30s} | 规范号: {code:15s} | 结果: {result}")
    
    print()


if __name__ == "__main__":
    test_spec_code_pattern()
    test_spec_code_parser()
    test_validation()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
