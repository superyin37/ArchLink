# Spec Locator Service - 快速启动

## 配置说明

### 环境变量配置

项目支持通过环境变量进行配置。创建 `.env` 文件或设置系统环境变量：

**主要配置项：**
- `SPEC_DATA_DIR`: 规范文件索引目录（默认：`../output_pages`）
- `API_PORT`: API服务端口（默认：`8000`）
- `LOG_LEVEL`: 日志级别（默认：`INFO`）
- `DEBUG`: 调试模式（默认：`false`）

**配置方法：**
1. 复制 `.env.example` 为 `.env`
2. 根据实际情况修改配置值
3. 或在启动脚本中设置环境变量

## 启动服务

**方式1：使用启动脚本（推荐）**
```bat
start_demo.bat
```

**方式2：手动启动**
```powershell
cd D:\projects\liuzong\spec_locator
.\.venv\Scripts\Activate.ps1
cd ..
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002
```

浏览器打开
http://127.0.0.1:8002/docs

演示页面
file:///D:/projects/liuzong/spec_locator/api/demo.html

## 功能特性

✅ **规范编号识别** - 从CAD截图识别规范编号（如 12J2）
✅ **页码识别** - 识别对应页码（如 C11）
✅ **文件索引** - 自动索引 output_pages 目录中的PDF文件（2680+ 个文件）
✅ **智能匹配** - 根据识别结果自动查找对应的PDF文件
✅ **文件下载** - 提供PDF文件下载端点

## API 端点

### 1. 健康检查
```
GET /health
```
返回服务状态和索引统计信息

### 2. 规范定位识别
```
POST /api/spec-locate
```
上传CAD截图，返回识别结果和对应的PDF文件信息

### 3. 文件下载
```
GET /api/download/{spec_code}/{page_code}
```
直接下载指定规范和页码的PDF文件

## 示例响应

```json
{
  "success": true,
  "spec": {
    "code": "23J909",
    "page": "1-11",
    "confidence": 0.88
  },
  "file": {
    "path": "D:\\...\\output_pages\\23J909 工程做法\\23J909_1-11.pdf",
    "name": "23J909_1-11.pdf",
    "directory": "23J909 工程做法（高清）"
  },
  "candidates": [...]
}
```