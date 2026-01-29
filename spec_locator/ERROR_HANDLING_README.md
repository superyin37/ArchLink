# 错误处理增强 - 快速参考

## 🎯 更新目标
让用户明确知道识别失败的具体原因，而不是只显示"识别失败"。

## ✨ 核心改进

### 1. 三类错误场景的明确区分

| 场景 | 错误码 | 用户看到的信息 |
|------|--------|----------------|
| 图片质量差，OCR失败 | `NO_TEXT` | "未能从图像中识别到有效文本" + OCR文本列表 |
| 识别到文本，但没有规范号 | `NO_SPEC_CODE` | "未能识别到规范编号" + OCR文本列表 |
| 识别到规范号，但没有页码 | `NO_PAGE_CODE` | "未能识别到页码" + 规范号列表 + OCR文本 |
| 规范号和页码都有，但无法匹配 | `NO_MATCH` | "无法组合" + 规范号列表 + 页码列表 + OCR文本 |
| 识别成功，但数据库无文件 | `SUCCESS` + `warning` | 显示识别结果 + 黄色警告框 |

### 2. API 响应增强

**失败响应新增 `details` 字段：**
```json
{
  "success": false,
  "error_code": "NO_PAGE_CODE",
  "message": "未能识别到页码...",
  "details": {
    "ocr_texts": ["识别到的所有文本"],
    "ocr_count": 5,
    "identified_spec_codes": ["12J2"],
    "identified_page_codes": []
  }
}
```

**成功响应新增字段：**
```json
{
  "success": true,
  "spec": {...},
  "file": null,
  "file_found": false,  // 新增
  "warning": "识别成功：12J2 C11-2，但数据库中未找到对应文件"  // 新增
}
```

### 3. 前端展示改进

- **详细错误信息**：显示具体失败原因和识别到的中间结果
- **OCR文本列表**：查看系统识别到的所有文本，帮助诊断问题
- **警告提示**：识别成功但文件未找到时，显示黄色警告框
- **中文友好**：所有提示信息都是中文，易于理解

## 📁 修改的文件

1. `spec_locator/config/config.py` - 错误码和消息
2. `spec_locator/core/pipeline.py` - Pipeline处理逻辑
3. `spec_locator/api/demo.html` - 前端展示
4. `spec_locator/ERROR_HANDLING_ENHANCEMENT.md` - 详细文档
5. `spec_locator/tests/test_error_handling_enhancement.py` - 测试脚本

## 🚀 快速测试

```bash
# 运行测试脚本查看响应格式
cd spec_locator
python tests/test_error_handling_enhancement.py
```

## 📖 完整文档

详细的技术说明和使用场景请参考：
- [ERROR_HANDLING_ENHANCEMENT.md](ERROR_HANDLING_ENHANCEMENT.md)

## 🎉 效果对比

### 之前
```
❌ 识别失败
```

### 现在
```
❌ 未能识别到页码。请确保图像中包含页码信息（如：C11、C11-2等）。

✓ 已识别到的规范编号：
12J2

OCR识别到的所有文本 (3个)：
• 12J2
• 详图
• 说明
```

---

**版本**：v1.1.0  
**更新日期**：2026-01-28  
**兼容性**：向后兼容，不影响现有客户端
