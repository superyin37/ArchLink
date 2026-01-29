"""
页码识别能力实际测试
测试不同格式的页码是否能被正则表达式匹配
"""
import re

print("=" * 80)
print("页码识别能力分析 - 正则表达式测试")
print("=" * 80)

# ========== 1. PageByAnchorExtractor 的 PAGE_PATTERN ==========
print("\n【1】PageByAnchorExtractor.PAGE_PATTERN")
print("-" * 80)
print("正则表达式: r\"^[A-Z]?\\d+$\"")
print("说明: 可选的单字母 + 一个或多个数字")

PAGE_PATTERN = re.compile(r"^[A-Z]?\d+$", re.IGNORECASE)

test_cases_anchor = [
    ("C11", True, "字母+数字"),
    ("P5", True, "字母+数字"),
    ("11", True, "纯两位数字"),
    ("5", True, "纯单数字"),
    ("123", True, "纯三位数字"),
    ("C11-2", False, "带连字符"),
    ("1-11", False, "纯数字带连字符"),
    ("AB11", False, "多字母前缀"),
    ("ABC", False, "纯字母"),
    ("C", False, "单字母"),
]

print("\n测试结果:")
for text, expected, desc in test_cases_anchor:
    result = bool(PAGE_PATTERN.match(text))
    status = "✅" if result == expected else "❌"
    match_str = "匹配" if result else "不匹配"
    print(f"  {status} '{text:10}' → {match_str:8} ({desc})")

# ========== 2. LegacyPageCodeParser 的 PREFIX_PATTERN ==========
print("\n\n【2】LegacyPageCodeParser - PAGE_PREFIX_PATTERN")
print("-" * 80)
print("正则表达式: r\"([A-Z])(\\d{1,3})\"")
print("说明: 单字母 + 1-3位数字")

PAGE_PREFIX_PATTERN = r"([A-Z])(\d{1,3})"

test_cases_prefix = [
    ("C11", True, "单字母+两位数字"),
    ("P5", True, "单字母+单数字"),
    ("A123", True, "单字母+三位数字"),
    ("11", False, "纯数字（无字母）"),
    ("AB11", False, "多字母前缀"),
    ("C", False, "只有字母"),
    ("C1234", False, "四位数字（超出范围）"),
]

print("\n测试结果:")
for text, expected, desc in test_cases_prefix:
    result = bool(re.match(PAGE_PREFIX_PATTERN, text))
    status = "✅" if result == expected else "❌"
    match_str = "匹配" if result else "不匹配"
    print(f"  {status} '{text:10}' → {match_str:8} ({desc})")

# ========== 3. LegacyPageCodeParser 的 SUFFIX_PATTERN ==========
print("\n\n【3】LegacyPageCodeParser - SUFFIX_PATTERN")
print("-" * 80)
print("正则表达式: r\"^\\d{1,2}$\"")
print("说明: 1-2位纯数字 (要求置信度 > 0.7)")

SUFFIX_PATTERN = r"^\d{1,2}$"

test_cases_suffix = [
    ("1", True, "单数字"),
    ("11", True, "两位数字"),
    ("123", False, "三位数字（超出范围）"),
    ("C11", False, "包含字母"),
    ("1-2", False, "带连字符"),
]

print("\n测试结果:")
for text, expected, desc in test_cases_suffix:
    result = bool(re.match(SUFFIX_PATTERN, text))
    status = "✅" if result == expected else "❌"
    match_str = "匹配" if result else "不匹配"
    print(f"  {status} '{text:10}' → {match_str:8} ({desc})")

# ========== 4. 文件索引的页码提取模式 ==========
print("\n\n【4】FileIndex - 文件名页码提取")
print("-" * 80)
print("多种模式按优先级匹配")

file_patterns = [
    (r'_([A-Z]\d+(?:-\d+)?)', "字母+数字，可选连字符"),
    (r'_(\d+-\d+)', "纯数字带连字符"),
    (r'_([A-Z]+\d+)', "多字母+数字"),
    (r'_(\d+)', "纯数字"),
]

test_files = [
    ("23J909_C11.pdf", "C11", "字母+数字"),
    ("23J909_C11-2.pdf", "C11-2", "字母+数字带连字符"),
    ("23J909_1-11.pdf", "1-11", "纯数字带连字符"),
    ("23J909_11.pdf", "11", "纯数字"),
    ("23J909_5.pdf", "5", "单数字"),
    ("23J909_123.pdf", "123", "三位数字"),
    ("23J909_ABC123.pdf", "ABC123", "多字母+数字"),
]

print("\n测试结果:")
for filename, expected, desc in test_files:
    name = filename.replace('.pdf', '')
    matched = None
    for pattern, _ in file_patterns:
        match = re.search(pattern, name)
        if match:
            matched = match.group(1)
            break
    
    status = "✅" if matched == expected else "❌"
    result_str = matched if matched else "未匹配"
    print(f"  {status} '{filename:25}' → {result_str:10} ({desc})")

# ========== 5. 综合分析 ==========
print("\n\n【5】综合分析：OCR识别 vs 文件索引")
print("=" * 80)

test_comprehensive = [
    ("C11", True, True, "字母+数字"),
    ("P5", True, True, "字母+数字"),
    ("11", True, True, "两位纯数字"),
    ("5", True, True, "单数字"),
    ("123", True, True, "三位数字（锚点✅/旧版❌）"),
    ("C11-2", False, True, "带连字符（识别失败但文件支持）"),
    ("1-11", False, True, "纯数字连字符（识别失败但文件支持）"),
]

print("\n格式对比:")
print(f"{'页码格式':<12} {'OCR识别':<12} {'文件索引':<12} {'说明'}")
print("-" * 80)

for page_code, ocr_support, file_support, desc in test_comprehensive:
    ocr_str = "✅ 支持" if ocr_support else "❌ 不支持"
    file_str = "✅ 支持" if file_support else "❌ 不支持"
    print(f"{page_code:<12} {ocr_str:<12} {file_str:<12} {desc}")

print("\n" + "=" * 80)
print("关键发现:")
print("1. ✅ 纯数字页码（11, 5, 123）能被识别")
print("2. ❌ 带连字符的页码（C11-2, 1-11）不能被OCR识别")
print("3. ⚠️  文件支持的格式比OCR识别能力更强")
print("4. 💡 建议: 扩展 PAGE_PATTERN 支持连字符")
print("=" * 80)
