# PDF预览与下载功能一致性修复

## 问题描述

之前系统存在PDF阅览功能提供的图片和下载功能提供的PDF不一致的问题。

## 根本原因

两个API使用了**完全不同的页面检索逻辑**：

### 修复前的问题

#### 1. 下载API (`/api/download/{spec_code}/{page_code}`)
```python
pdf_file = pipeline.file_index.find_file(spec_code, page_code)
```
- ✅ 使用 `find_file(spec_code, page_code)` 精确查找
- ✅ 根据页码编号（如 C11、1-11）找到对应的PDF文件

#### 2. 预览API (`/api/pdf-page-preview`) - 修复前
```python
spec_files = pipeline.file_index.get_spec_files(spec_code)
pdf_file = spec_files[0]  # ❌ 直接使用第一个文件
```
- ❌ 获取该规范的所有文件后直接取第一个
- ❌ 完全忽略了页码编号
- ❌ 对于有多个PDF文件的规范，总是返回第一个文件的内容

### 不一致示例

假设 `12J2` 规范有以下文件：
- `12J2_C11-1.pdf`
- `12J2_C11-2.pdf`
- `12J2_C11-3.pdf`

**用户请求：** 查看 `12J2` 的 `C11-2` 页面

- **下载功能：** ✅ 正确返回 `12J2_C11-2.pdf`
- **预览功能（修复前）：** ❌ 返回 `12J2_C11-1.pdf` 的内容

## 修复方案

### API参数调整

将预览API的参数结构调整为与下载API一致：

**修复前：**
```python
@app.get("/api/pdf-page-preview")
async def pdf_page_preview(
    spec_code: str,    # 规范编号
    page_number: int,  # ❌ 数字页码（PDF内部索引）
    dpi: int = 150
)
```

**修复后：**
```python
@app.get("/api/pdf-page-preview")
async def pdf_page_preview(
    spec_code: str,    # 规范编号
    page_code: str,    # ✅ 页码编号（如 C11, 1-11）
    page_number: int = 1,  # ✅ PDF内部页码，默认第1页
    dpi: int = 150
)
```

### 文件查找逻辑统一

**修复后的核心代码：**
```python
# 使用与下载功能相同的文件查找逻辑
pdf_file = pipeline.file_index.find_file(spec_code, page_code)

if not pdf_file:
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error_code": "FILE_NOT_FOUND",
            "message": f"未找到 {spec_code} 页码 {page_code} 对应的PDF文件",
        }
    )

# 使用page_number定位PDF内部的具体页面
doc = fitz.open(pdf_file.file_path)
page = doc.load_page(page_number - 1)
```

## 修复效果

### 参数语义明确
- `page_code`: 用于定位具体的PDF文件（与文件名中的页码编号对应）
- `page_number`: 用于定位该PDF文件内的具体页面（默认为1）

### 功能一致性
- ✅ 预览和下载使用相同的文件查找逻辑
- ✅ 能正确处理多文件规范的情况
- ✅ 避免了"预览显示A文件、下载得到B文件"的问题

### 缓存键调整
```python
# 修复前
cache_key = f"{spec_code}_{page_number}_{dpi}"

# 修复后
cache_key = f"{spec_code}_{page_code}_{page_number}_{dpi}"
```
缓存现在基于正确的文件标识，避免不同页码文件的缓存冲突。

## API使用示例

### 基本用法（预览PDF第1页）
```bash
GET /api/pdf-page-preview?spec_code=12J2&page_code=C11-2&dpi=150
# 默认page_number=1，预览 12J2_C11-2.pdf 的第1页
```

### 预览PDF的其他页面
```bash
GET /api/pdf-page-preview?spec_code=12J2&page_code=C11-2&page_number=2&dpi=150
# 预览 12J2_C11-2.pdf 的第2页
```

### JavaScript调用示例
```javascript
// 预览指定页码的PDF
async function previewPDF(specCode, pageCode, pageNumber = 1, dpi = 150) {
    const url = `${API_BASE_URL}/api/pdf-page-preview`;
    const params = new URLSearchParams({
        spec_code: specCode,
        page_code: pageCode,
        page_number: pageNumber.toString(),
        dpi: dpi.toString()
    });
    
    const response = await fetch(`${url}?${params}`);
    if (response.ok) {
        const blob = await response.blob();
        return URL.createObjectURL(blob);
    }
    throw new Error('Preview failed');
}

// 使用示例
const imageUrl = await previewPDF('12J2', 'C11-2', 1, 150);
document.getElementById('preview').src = imageUrl;
```

## 测试更新

测试文件 `test_pdf_preview.py` 已更新，使用新的API参数：

```python
test_cases = [
    {"spec_code": "12J2", "page_code": "02", "page_number": 1, "dpi": 150},
    {"spec_code": "12J2", "page_code": "A10", "page_number": 1, "dpi": 150},
    {"spec_code": "15J401", "page_code": "5", "page_number": 1, "dpi": 150},
    {"spec_code": "15J401", "page_code": "A1", "page_number": 1, "dpi": 200},
]
```

运行测试：
```bash
cd spec_locator
python test_pdf_preview.py
```

## 影响范围

### 需要更新的前端代码

如果前端已经在使用预览API，需要更新调用方式：

**更新前：**
```javascript
fetch(`/api/pdf-page-preview?spec_code=12J2&page_number=5`)
```

**更新后：**
```javascript
fetch(`/api/pdf-page-preview?spec_code=12J2&page_code=C11-2&page_number=1`)
```

### 不受影响的部分
- 下载API (`/api/download`) 保持不变
- 图集定位API (`/api/spec-locate`) 保持不变
- 文件索引逻辑保持不变

## 兼容性说明

这个修复提供了**向后兼容**：
- ✅ 支持旧的调用方式（不提供 `page_code` 参数）
- ✅ 支持新的调用方式（提供 `page_code` 参数，推荐）
- ⚠️ 旧方式仍存在不一致问题，建议逐步迁移到新方式
- 📝 使用旧方式时会在日志中记录警告

### 调用方式对比

**旧方式（向后兼容，但可能不一致）：**
```javascript
// 不提供page_code，使用规范下的第一个文件
GET /api/pdf-page-preview?spec_code=12J2&page_number=1
```

**新方式（推荐，确保一致性）：**
```javascript
// 提供page_code，与下载功能保持一致
GET /api/pdf-page-preview?spec_code=12J2&page_code=C11-2&page_number=1
```

## 修复日期

2026年2月2日

## 相关文件

- `spec_locator/api/server.py` - 主要修复
- `spec_locator/test_pdf_preview.py` - 测试更新
- `spec_locator/database/file_index.py` - 文件索引（无变更）
