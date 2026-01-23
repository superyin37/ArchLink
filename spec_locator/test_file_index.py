"""
测试文件索引功能
"""

from spec_locator.database import FileIndex

# 初始化索引
print("Building file index...")
index = FileIndex()

# 显示统计信息
stats = index.get_stats()
print(f"\n索引统计:")
print(f"  规范编号数量: {stats['spec_codes']}")
print(f"  文件总数: {stats['total_files']}")

# 显示所有规范编号
print(f"\n已索引的规范编号:")
for spec_code in sorted(index.get_all_specs())[:10]:
    files = index.get_spec_files(spec_code)
    print(f"  {spec_code}: {len(files)} 个文件")

# 测试查找
print(f"\n测试查找:")
test_cases = [
    ("23J909", "1-11"),
    ("06J908-1", "C11"),
    ("12J2", "C11"),  # 这个可能找不到
]

for spec_code, page_code in test_cases:
    result = index.find_file(spec_code, page_code)
    if result:
        print(f"  ✓ {spec_code} 页 {page_code}: {result.file_name}")
    else:
        print(f"  ✗ {spec_code} 页 {page_code}: 未找到")
