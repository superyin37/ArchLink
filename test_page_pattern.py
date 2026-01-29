import re

# 当前的 PAGE_PATTERN
PAGE_PATTERN = re.compile(r"^[A-Z]?\d+$", re.IGNORECASE)

test_cases = [
    "C11",      # 字母+数字 (应该匹配)
    "11",       # 纯数字 (应该匹配)
    "1",        # 单数字 (应该匹配)
    "123",      # 多位数字 (应该匹配)
    "P5",       # 字母+数字 (应该匹配)
    "5-2",      # 数字-数字 (不应该匹配，包含连字符)
    "C11-2",    # 字母+数字-数字 (不应该匹配，包含连字符)
    "1-11",     # 数字-数字 (不应该匹配)
]

print("当前 PAGE_PATTERN 测试结果: r\"^[A-Z]?\\d+$\"")
print("-" * 60)
for text in test_cases:
    match = PAGE_PATTERN.match(text)
    print(f"  '{text:12}' : {'✓ 匹配' if match else '✗ 不匹配'}")

print("\n" + "=" * 60)
print("\n问题分析：")
print("1. 当前模式 [A-Z]? 表示字母可选，所以纯数字应该能匹配")
print("2. 但是包含连字符的页码（如 1-11, C11-2）不能匹配")
print("3. 如果实际页码是 '1-11' 这种格式，当前模式会失败")
