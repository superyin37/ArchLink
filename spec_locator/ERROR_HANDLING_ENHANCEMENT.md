# 错误处理增强更新说明

## 更新时间
2026-01-28

## 更新概述
优化了规范号+页码识别系统的错误处理机制，提供更详细的错误信息和识别结果反馈，帮助用户更好地理解识别失败的原因。

## 主要改进

### 1. 错误码扩展 (config/config.py)

#### 新增错误码
- `FILE_NOT_FOUND_IN_DB`: 识别成功但数据库中未找到对应文件

#### 错误消息中文化
所有错误消息现在提供中文提示，更友好易懂：
- `NO_TEXT`: "未能从图像中识别到有效文本。请确保图片清晰，包含规范编号和页码信息。"
- `NO_SPEC_CODE`: "未能识别到规范编号。请确保图像中包含规范编号（如：12J2、20G908-1等）。"
- `NO_PAGE_CODE`: "未能识别到页码。请确保图像中包含页码信息（如：C11、C11-2等）。"
- `NO_MATCH`: "无法将识别到的规范编号和页码进行有效组合。"
- `FILE_NOT_FOUND_IN_DB`: "已识别到规范编号和页码，但数据库中未找到对应的规范文件。"

### 2. Pipeline 层错误详情增强 (core/pipeline.py)

#### _error_response 方法增强
现在返回更详细的识别信息：

```python
def _error_response(
    self, 
    error_code: ErrorCode, 
    ocr_texts: Optional[List[str]] = None,
    spec_codes: Optional[List[str]] = None,
    page_codes: Optional[List[str]] = None
) -> Dict[str, Any]
```

**返回内容包括：**
- `error_code`: 错误码
- `message`: 中文错误消息
- `details`: 详细识别信息
  - `ocr_texts`: OCR识别到的所有文本列表
  - `ocr_count`: 识别到的文本数量
  - `identified_spec_codes`: 识别到的规范编号列表
  - `identified_page_codes`: 识别到的页码列表

#### 错误响应示例

**完全识别失败（NO_TEXT）：**
```json
{
  "success": false,
  "error_code": "NO_TEXT",
  "message": "未能从图像中识别到有效文本。请确保图片清晰，包含规范编号和页码信息。",
  "details": {
    "ocr_texts": [],
    "ocr_count": 0
  }
}
```

**识别到文本但未找到规范号（NO_SPEC_CODE）：**
```json
{
  "success": false,
  "error_code": "NO_SPEC_CODE",
  "message": "未能识别到规范编号。请确保图像中包含规范编号（如：12J2、20G908-1等）。",
  "details": {
    "ocr_texts": ["C11", "2", "某些其他文本"],
    "ocr_count": 3
  }
}
```

**识别到规范号但未找到页码（NO_PAGE_CODE）：**
```json
{
  "success": false,
  "error_code": "NO_PAGE_CODE",
  "message": "未能识别到页码。请确保图像中包含页码信息（如：C11、C11-2等）。",
  "details": {
    "ocr_texts": ["12J2", "某些文本"],
    "ocr_count": 2,
    "identified_spec_codes": ["12J2"]
  }
}
```

**识别到规范号和页码但无法匹配（NO_MATCH）：**
```json
{
  "success": false,
  "error_code": "NO_MATCH",
  "message": "无法将识别到的规范编号和页码进行有效组合。",
  "details": {
    "ocr_texts": ["12J2", "C11", "20G908-1", "P5"],
    "ocr_count": 4,
    "identified_spec_codes": ["12J2", "20G908-1"],
    "identified_page_codes": ["C11", "P5"]
  }
}
```

#### _success_response 方法增强
成功识别但数据库中未找到文件时，添加警告信息：

```json
{
  "success": true,
  "spec": {
    "code": "12J2",
    "page": "C11-2",
    "confidence": 0.93
  },
  "file": null,
  "file_found": false,
  "warning": "识别成功：12J2 C11-2，但数据库中未找到对应文件",
  "candidates": [...]
}
```

### 3. 前端展示增强 (api/demo.html)

#### showError 函数重写
支持显示详细的错误信息和识别中间结果：

**功能特性：**
1. **显示主要错误消息**：清晰的中文错误提示
2. **显示识别到的规范编号**：如果识别到规范号，会在错误信息中显示
3. **显示识别到的页码**：如果识别到页码，会在错误信息中显示
4. **显示OCR文本列表**：显示所有OCR识别到的文本，帮助诊断问题

**界面展示样式：**
- 错误消息以红色背景卡片形式展示
- 识别到的信息以半透明白色背景区块显示
- OCR文本列表支持滚动，最大高度120px
- 使用符号标记不同类型的信息（✓、❌、•）

#### displayResult 函数增强
支持显示文件未找到的警告：
- 当 `warning` 字段存在时，在识别结果中显示黄色警告提示框
- 提示用户识别成功但数据库中没有对应文件

## 使用场景示例

### 场景 1：图片模糊，OCR完全失败
**错误信息：**
```
❌ 未能从图像中识别到有效文本。请确保图片清晰，包含规范编号和页码信息。

OCR识别到的所有文本 (0个)：
（无文本）
```

### 场景 2：识别到文本，但不包含规范号
**错误信息：**
```
❌ 未能识别到规范编号。请确保图像中包含规范编号（如：12J2、20G908-1等）。

OCR识别到的所有文本 (5个)：
• C11
• 2
• 详图
• 示意图
• 说明
```

### 场景 3：识别到规范号，但未找到页码
**错误信息：**
```
❌ 未能识别到页码。请确保图像中包含页码信息（如：C11、C11-2等）。

✓ 已识别到的规范编号：
12J2

OCR识别到的所有文本 (3个)：
• 12J2
• 详图
• 说明
```

### 场景 4：规范号和页码都识别到，但数据库中无文件
**成功信息：**
```
✅ 识别结果
规范编号: 12J2
页码: C11-2
置信度: 93.0%

⚠️ 提示： 识别成功：12J2 C11-2，但数据库中未找到对应文件
```

## API 响应格式变化

### 成功响应（找到文件）
```json
{
  "success": true,
  "spec": {
    "code": "12J2",
    "page": "C11-2",
    "confidence": 0.93
  },
  "file": {
    "path": "/path/to/file.pdf",
    "name": "12J2-C11-2.pdf",
    "directory": "12J2",
    "download_url": "/api/download/12J2/C11-2"
  },
  "file_found": true,
  "candidates": [...]
}
```

### 成功响应（未找到文件）
```json
{
  "success": true,
  "spec": {
    "code": "12J2",
    "page": "C11-2",
    "confidence": 0.93
  },
  "file": null,
  "file_found": false,
  "warning": "识别成功：12J2 C11-2，但数据库中未找到对应文件",
  "candidates": [...]
}
```

### 失败响应（包含识别详情）
```json
{
  "success": false,
  "error_code": "NO_PAGE_CODE",
  "message": "未能识别到页码。请确保图像中包含页码信息（如：C11、C11-2等）。",
  "details": {
    "ocr_texts": ["12J2", "某些文本", "更多内容"],
    "ocr_count": 3,
    "identified_spec_codes": ["12J2"]
  }
}
```

## 技术细节

### 修改的文件
1. `spec_locator/config/config.py` - 错误码和错误消息定义
2. `spec_locator/core/pipeline.py` - Pipeline核心处理逻辑
3. `spec_locator/api/demo.html` - 前端展示逻辑

### 兼容性
- **向后兼容**：原有的 `success`、`error_code`、`message` 字段保持不变
- **新增字段**：`details`、`warning`、`file_found` 为新增字段，不会影响现有客户端
- **API版本**：无需更新API版本号，新字段为可选扩展

## 测试建议

### 测试用例
1. **完全识别失败**：上传一张不包含任何文本的图片
2. **无规范号**：上传只包含页码信息的图片
3. **无页码**：上传只包含规范号的图片
4. **识别成功但无文件**：上传包含规范号+页码，但数据库中不存在的组合
5. **完全成功**：上传正常的CAD截图，包含规范号+页码且数据库中有对应文件

### 验证要点
- 错误消息是否清晰易懂
- 识别到的中间结果是否正确显示
- OCR文本列表是否完整
- 文件未找到警告是否正确显示

## 未来改进建议

1. **日志增强**：在服务器端记录详细的识别过程，便于问题诊断
2. **相似匹配提示**：当数据库中没有精确匹配时，提供相似的规范号+页码组合建议
3. **识别置信度阈值调整**：允许用户调整识别的置信度阈值
4. **批量识别报告**：支持批量上传图片并生成识别报告
5. **人工修正反馈**：允许用户修正识别结果，用于改进模型

## 结论

此次更新显著提升了系统的用户体验，使用户能够：
- **明确知道识别失败的具体原因**：规范号识别失败、页码识别失败还是数据库中没有文件
- **查看识别到的中间结果**：即使最终失败，也能看到系统识别到了哪些内容
- **快速诊断问题**：通过查看OCR文本列表，可以判断是图片质量问题还是系统识别问题

这些改进使系统从"黑盒"变为"白盒"，大大提高了可调试性和用户满意度。
