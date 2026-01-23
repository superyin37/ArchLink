# 规范定位识别系统 - 使用指南

## 功能说明

本系统可以：
1. 上传 CAD 截图
2. 自动识别规范编号和页码
3. 在数据库中查找对应的 PDF 文件
4. **自动提供下载链接**（新增功能）

## 快速启动

### 方式一：使用启动脚本（推荐）

```bash
# Windows
start_demo.bat

# 会自动：
# 1. 激活虚拟环境
# 2. 启动 API 服务器
# 3. 打开演示页面
```

### 方式二：手动启动

```bash
# 1. 激活虚拟环境
.venv\Scripts\activate

# 2. 启动服务器
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8000 --reload

# 3. 在浏览器中打开
# file:///D:/projects/liuzong/spec_locator/api/demo.html
```

## API 端点说明

### 1. POST `/api/spec-locate` - 识别规范

**请求：**
```bash
curl -X POST http://127.0.0.1:8000/api/spec-locate \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@cad_example_01.png;type=image/png"
```

**响应示例（找到文件）：**
```json
{
  "success": true,
  "spec": {
    "code": "12J2",
    "page": "C11",
    "confidence": 0.7834
  },
  "candidates": [
    {
      "code": "12J2",
      "page": "C11",
      "confidence": 0.7834
    }
  ],
  "file": {
    "path": "D:\\projects\\liuzong\\output_pages\\12J2\\12J2_C11.pdf",
    "name": "12J2_C11.pdf",
    "directory": "12J2",
    "download_url": "/api/download/12J2/C11"  ← 新增：下载URL
  }
}
```

**响应示例（未找到文件）：**
```json
{
  "success": true,
  "spec": {
    "code": "12J2",
    "page": "C11",
    "confidence": 0.7834
  },
  "candidates": [...],
  "file": null  ← 表示未找到对应的PDF文件
}
```

### 2. GET `/api/download/{spec_code}/{page_code}` - 下载PDF

**请求：**
```bash
# 浏览器访问
http://127.0.0.1:8000/api/download/12J2/C11

# 或使用 curl
curl -O http://127.0.0.1:8000/api/download/12J2/C11
```

**响应：**
- 成功：返回 PDF 文件（Content-Type: application/pdf）
- 失败：返回错误信息 JSON

## 前端集成指南

### 1. 上传并识别图片

```javascript
async function uploadImage(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://127.0.0.1:8000/api/spec-locate', {
    method: 'POST',
    body: formData
  });

  return await response.json();
}
```

### 2. 处理响应并下载PDF

```javascript
const result = await uploadImage(file);

if (result.success && result.file && result.file.download_url) {
  // 方案 A: 创建下载链接按钮
  const downloadBtn = document.createElement('a');
  downloadBtn.href = `http://127.0.0.1:8000${result.file.download_url}`;
  downloadBtn.download = result.file.name;
  downloadBtn.textContent = '下载 PDF';
  downloadBtn.click();

  // 方案 B: 在新窗口打开
  window.open(`http://127.0.0.1:8000${result.file.download_url}`, '_blank');

  // 方案 C: 自动下载（用户体验可能不佳）
  const link = document.createElement('a');
  link.href = `http://127.0.0.1:8000${result.file.download_url}`;
  link.download = result.file.name;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
} else {
  console.log('未找到对应的PDF文件');
}
```

### 3. 完整示例

参考 [api/demo.html](api/demo.html) 查看完整的前端实现示例。

## 演示页面功能

打开 `api/demo.html` 后，你可以：

1. ✅ 点击或拖拽上传 CAD 截图
2. ✅ 实时预览上传的图片
3. ✅ 查看识别结果（规范编号、页码、置信度）
4. ✅ **一键下载对应的 PDF 文件**（当文件存在时）
5. ✅ 查看其他候选结果

## 工作流程

```
用户上传图片
    ↓
POST /api/spec-locate
    ↓
OCR识别 + 解析规范和页码
    ↓
在文件索引中查找PDF
    ↓
返回识别结果 + 下载URL（如果找到文件）
    ↓
前端显示下载按钮
    ↓
用户点击下载
    ↓
GET /api/download/{spec_code}/{page_code}
    ↓
浏览器下载PDF文件
```

## 注意事项

1. **确保数据已准备**：`output_pages` 目录中需要有已分页的PDF文件
2. **CORS已配置**：服务器已添加CORS支持，前端可以跨域访问
3. **文件大小限制**：默认最大上传 10MB
4. **支持的图片格式**：png, jpg, jpeg, bmp, gif, tiff

## 故障排查

### 问题：点击下载没反应

**原因：** 文件路径不正确或文件不存在

**解决：**
```bash
# 检查文件是否存在
GET /health

# 查看日志
# 日志中会显示 "PDF file not found" 或 "File not found on disk"
```

### 问题：前端无法访问API

**原因：** CORS未配置或服务器未启动

**解决：**
```bash
# 1. 确认服务器正在运行
http://127.0.0.1:8000/health

# 2. 检查浏览器控制台是否有CORS错误
# 3. 确认server.py中已添加CORS中间件
```

### 问题：识别不准确

**原因：** OCR置信度阈值过低或图片质量不佳

**解决：**
1. 使用清晰的截图
2. 确保规范编号和页码清晰可见
3. 调整 OCR 阈值（在 pipeline 初始化时）

## 更新日志

### v1.1.0 (2026-01-20)
- ✅ 在 POST 响应中添加 `download_url` 字段
- ✅ 添加 CORS 支持，允许前端跨域访问
- ✅ 创建演示 HTML 页面
- ✅ 创建启动脚本 `start_demo.bat`

### v1.0.0
- ✅ 基础识别功能
- ✅ 文件索引功能
- ✅ GET 下载端点

## 技术栈

- **后端：** FastAPI + PaddleOCR
- **前端：** 原生 HTML + JavaScript
- **存储：** 文件系统索引
