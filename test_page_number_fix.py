"""
测试纯数字页码识别修复
"""
import sys
sys.path.insert(0, 'spec_locator')

from spec_locator.parser.page_code import LegacyPageCodeParser, PagePart
from spec_locator.ocr.ocr_engine import TextBox

# 模拟 OCR 结果
def create_mock_boxes():
    """创建模拟的 OCR 文本框"""
    boxes = [
        # 纯数字页码（应该被识别）
        TextBox(text="11", confidence=0.85, box=[[100, 100], [130, 100], [130, 130], [100, 130]]),
        TextBox(text="5", confidence=0.90, box=[[200, 100], [220, 100], [220, 130], [200, 130]]),
        TextBox(text="123", confidence=0.75, box=[[300, 100], [340, 100], [340, 130], [300, 130]]),
        
        # 字母+数字页码（应该被识别）
        TextBox(text="C11", confidence=0.88, box=[[100, 200], [140, 200], [140, 230], [100, 230]]),
        TextBox(text="P5", confidence=0.92, box=[[200, 200], [230, 200], [230, 230], [200, 230]]),
        
        # 非页码文本（不应该被识别）
        TextBox(text="建筑", confidence=0.95, box=[[400, 100], [450, 100], [450, 130], [400, 130]]),
        TextBox(text="ABC", confidence=0.80, box=[[500, 100], [540, 100], [540, 130], [500, 130]]),
    ]
    return boxes

def test_legacy_parser():
    """测试旧版解析器"""
    print("=" * 70)
    print("测试 LegacyPageCodeParser - 纯数字页码识别修复")
    print("=" * 70)
    
    parser = LegacyPageCodeParser(max_distance=100)
    boxes = create_mock_boxes()
    
    print("\n输入的 OCR 文本框：")
    for i, box in enumerate(boxes):
        print(f"  [{i}] '{box.text}' (置信度: {box.confidence:.2f})")
    
    # 测试页码部分提取
    print("\n第1步：提取页码部分 (_extract_page_parts)")
    print("-" * 70)
    page_parts = parser._extract_page_parts(boxes)
    
    prefix_count = sum(1 for p in page_parts if p.part_type == "prefix")
    suffix_count = sum(1 for p in page_parts if p.part_type == "suffix")
    
    print(f"  找到 {len(page_parts)} 个页码部分（prefix: {prefix_count}, suffix: {suffix_count}）")
    for part in page_parts:
        print(f"    - '{part.text}' => {part.part_type} (置信度: {part.confidence:.2f})")
    
    # 测试页码组合
    print("\n第2步：组合页码 (_combine_page_parts)")
    print("-" * 70)
    page_codes = parser.parse(boxes)
    
    print(f"  最终识别到 {len(page_codes)} 个页码：")
    for pc in page_codes:
        print(f"    ✓ '{pc.page}' (置信度: {pc.confidence:.2f})")
    
    # 验证结果
    print("\n验证结果：")
    print("-" * 70)
    expected = {"11", "5", "123", "C11", "P5"}
    found = {pc.page for pc in page_codes}
    
    missing = expected - found
    extra = found - expected
    
    if not missing and not extra:
        print("  ✅ 所有预期页码都被正确识别")
    else:
        if missing:
            print(f"  ❌ 缺失的页码: {missing}")
        if extra:
            print(f"  ⚠️  额外识别的页码: {extra}")
    
    # 特别检查纯数字页码
    print("\n纯数字页码识别检查：")
    pure_numbers = {"11", "5", "123"}
    found_numbers = pure_numbers & found
    print(f"  预期: {pure_numbers}")
    print(f"  实际: {found_numbers}")
    if pure_numbers == found_numbers:
        print("  ✅ 纯数字页码识别正常")
    else:
        print(f"  ❌ 纯数字页码识别失败，缺失: {pure_numbers - found_numbers}")

if __name__ == "__main__":
    test_legacy_parser()
