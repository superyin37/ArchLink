# Spec Locator Service - CAD 规范定位识别服务

## 项目概述

**Spec Locator Service** 是一个专为建筑设计辅助软件设计的"以图搜图"服务。用户上传包含规范引用的 CAD 截图，系统自动识别其中的**建筑规范编号**与**页码**，并返回结构化识别结果。

## 核心特性

✅ **模块化设计** - 清晰的职责划分，易于维护和扩展  
✅ **独立部署** - 微服务架构，可独立运行和扩展  
✅ **稳定 API** - HTTP RESTful 接口，易于集成  
✅ **高准确率** - 多层验证和置信度评估机制  
✅ **容错能力** - 完善的错误处理和候选排序  

## 系统架构

```
输入图像
   ↓
[预处理] 去线、增强、二值化
   ↓
[OCR引擎] 文本识别 + 位置信息
   ↓
[解析层] 规范编号识别、页码组合
   ↓
[后处理] 置信度评估、结果排序
   ↓
结构化输出 (JSON)
```

## 模块结构

```
spec_locator/
├── config/              # 配置管理
│   └── config.py
├── preprocess/          # 图像预处理
│   └── image_preprocess.py
├── ocr/                 # OCR 引擎封装
│   └── ocr_engine.py
├── parser/              # 解析层
│   ├── spec_code.py     # 规范编号识别
│   ├── page_code.py     # 页码识别
│   └── geometry.py      # 几何关系计算
├── postprocess/         # 后处理
│   └── confidence.py    # 置信度评估
├── database/            # 文件索引（新增）
│   └── file_index.py    # PDF文件索引与查找
├── core/                # 核心流水线
│   └── pipeline.py
├── api/                 # HTTP API
│   └── server.py
├── tests/               # 测试
└── main.py              # 主程序入口
```

## 快速开始

### 安装依赖（3 种方式）

#### 方式 1️⃣：自动安装脚本（推荐）
```bash
# 自动检测并使用 uv 或 pip
python setup.py
```

#### 方式 2️⃣：使用 uv（最快，比 pip 快 10-100 倍）
```bash
# 一键安装（推荐）
uv sync --dev

# 或分步操作
uv venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"
```

#### 方式 3️⃣：使用 pip（传统方式）
```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装项目和依赖
pip install -e ".[dev]"
```

📖 **更多信息**：详见 [UV_GUIDE.md](UV_GUIDE.md)

### 启动服务

```bash
# 方式 1：直接运行
python main.py

# 方式 2：使用 uvicorn
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# 方式 3：指定 GPU
export OCR_USE_GPU=true
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 健康检查

```bash
curl http://localhost:8000/health
```

响应：
```json
{
  "status": "ok",
  "index_stats": {
    "spec_codes": 8,
    "total_files": 2680
  }
}
```

## API 使用

### 规范定位接口

**请求**

```bash
POST /api/spec-locate
Content-Type: multipart/form-data

file: <image_file>
```

**成功响应 (200)**

```json
{
  "success": true,
  "spec": {
    "code": "23J909",
    "page": "1-11",
    "confidence": 0.88
  },
  "file": {
    "path": "D:\\projects\\liuzong\\output_pages\\23J909 工程做法\\23J909_1-11.pdf",
    "name": "23J909_1-11.pdf",
    "directory": "23J909 工程做法（高清）"
  },
  "candidates": [
    {
      "code": "23J909",
      "page": "1-11",
      "confidence": 0.88
    },
    {
      "code": "23J909",
      "page": "1-10",
      "confidence": 0.45
    }
  ]
}

注意：如果未找到对应的PDF文件，`file` 字段将为 `null`
```

**失败响应 (200)**

```json
{
  "success": false,
  "error_code": "NO_SPEC_CODE",
  "message": "Failed to identify spec code from image."
}
```

### 错误码说明

| error_code | 含义 |
|-----------|------|
| NO_TEXT | 未识别到有效文本 |
| NO_SPEC_CODE | 未识别到规范编号 |
| NO_PAGE_CODE | 未识别到页码 |
| NO_MATCH | 无法组合有效结果 |
| INVALID_FILE | 无效的文件格式 |
| INTERNAL_ERROR | 内部服务错误 |

### Python 示例

```python
import requests

# 上传图片
with open("sample.png", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/api/spec-locate", files=files)

result = response.json()
if result["success"]:
    print(f"规范编号: {result['spec']['code']}")
    print(f"页码: {result['spec']['page']}")
    print(f"置信度: {result['spec']['confidence']}")
else:
    print(f"错误: {result['error_code']}")
```

### cURL 示例

```bash
curl -X POST http://localhost:8000/api/spec-locate \
  -F "file=@sample.png"
```

## 配置管理

编辑 `config/config.py` 调整参数：

```python
# OCR 配置
OCRConfig.USE_GPU = True  # 使用 GPU 加速
OCRConfig.CONF_THRESHOLD = 0.3  # OCR 置信度阈值

# 预处理配置
PreprocessConfig.ENHANCE_CONTRAST = True  # 增强对比度
PreprocessConfig.REMOVE_LINES = True  # 去除结构线

# 几何关系配置
GeometryConfig.MAX_DISTANCE = 100  # 最大邻近距离

# 置信度配置
ConfidenceConfig.MIN_CONFIDENCE = 0.1  # 最小置信度

# API 配置
APIConfig.HOST = "0.0.0.0"
APIConfig.PORT = 8000
APIConfig.MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行指定测试文件
pytest tests/test_spec_code.py -v

# 生成覆盖率报告
pytest --cov=. --cov-report=html
```

## 使用示例

### 完整的识别流程示例

```python
import cv2
import numpy as np
from core.pipeline import SpecLocatorPipeline

# 初始化流水线
pipeline = SpecLocatorPipeline()

# 读取图像
image = cv2.imread("cad_screenshot.png")

# 处理
result = pipeline.process(image)

# 输出结果
print(result)
```

### 单独使用各模块

```python
import cv2
from preprocess import ImagePreprocessor
from ocr import OCREngine
from parser import SpecCodeParser, PageCodeParser

# 预处理
preprocessor = ImagePreprocessor()
image = cv2.imread("sample.png")
processed = preprocessor.preprocess(image)

# OCR
ocr_engine = OCREngine()
text_boxes = ocr_engine.recognize(image)

# 解析
spec_parser = SpecCodeParser()
spec_codes = spec_parser.parse(text_boxes)

page_parser = PageCodeParser()
page_codes = page_parser.parse(text_boxes)
```

## 版本规划

- **v1.0** ✅ 基础版本 - 单规范识别
- **v1.1** 🔄 计划中 - 多规范同时识别
- **v1.2** 🔄 计划中 - 调试模式（OCR 可视化）
- **v2.0** 🔄 计划中 - 引入 AI 模型精准页码判断

## 性能指标

- **单张图片处理耗时**：300-500ms（CPU）/ 100-200ms（GPU）
- **内存占用**：～500MB（包含 OCR 模型）
- **支持文件格式**：PNG、JPG、JPEG
- **最大文件大小**：10MB
- **支持分辨率**：最大 4096×4096

## 部署指南

### Docker 部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .
RUN pip install -e ".[dev]"

EXPOSE 8000
CMD ["python", "main.py"]
```

```bash
# 构建镜像
docker build -t spec-locator:latest .

# 运行容器
docker run -p 8000:8000 spec-locator:latest
```

### 多进程部署（Nginx + Gunicorn）

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 api.server:app
```

## 常见问题

**Q: OCR 识别准确率不高怎么办？**  
A: 尝试调整 `PreprocessConfig.ENHANCE_CONTRAST` 参数，或提高图片质量。

**Q: 支持离线运行吗？**  
A: 支持。PaddleOCR 第一次运行会下载模型，之后即可离线使用。

**Q: 如何使用 GPU 加速？**  
A: 设置环境变量 `OCR_USE_GPU=true`，确保安装了 CUDA 和对应的 GPU 驱动。

---

## 新增功能 (v1.1.0 - 2026-01-20)

### 1. 自动下载功能

#### **功能描述**
POST请求识别成功后，如果在数据库中找到对应的PDF文件，响应中会自动包含下载URL，前端可直接使用该URL下载PDF。

#### **实现细节**
- 修改了 `core/pipeline.py` 的 `_success_response()` 方法
- 在响应中添加了 `file.download_url` 字段
- 格式：`/api/download/{spec_code}/{page_code}`

#### **响应示例**
```json
{
  "success": true,
  "spec": {
    "code": "12J2",
    "page": "C11",
    "confidence": 0.7834
  },
  "file": {
    "path": "D:\\projects\\liuzong\\output_pages\\12J2\\12J2_C11.pdf",
    "name": "12J2_C11.pdf",
    "directory": "12J2",
    "download_url": "/api/download/12J2/C11"  // 新增字段
  },
  "candidates": [...]
}
```

#### **使用方式**
```python
# Python示例
if result['file'] and result['file']['download_url']:
    download_url = f"http://api-server{result['file']['download_url']}"
    response = requests.get(download_url)
    with open('output.pdf', 'wb') as f:
        f.write(response.content)
```

---

### 2. 演示HTML界面

#### **功能描述**
创建了完整的前端演示页面 `api/demo.html`，提供用户友好的图形界面。

#### **主要功能**
- 📤 **拖拽/点击上传** - 支持多种图片格式（png, jpg, jpeg, bmp, gif, tiff）
- 🖼️ **实时预览** - 上传后立即显示图片
- ⏳ **加载动画** - 识别过程中的视觉反馈
- 📊 **结果展示** - 可视化显示规范编号、页码、置信度
- ⬇️ **一键下载** - 找到PDF文件时自动显示下载按钮
- 📋 **候选结果** - 显示其他可能的匹配结果
- ❌ **错误提示** - 友好的错误信息展示

#### **访问方式**
```bash
# 方式1：直接在浏览器打开本地文件
file:///D:/projects/liuzong/spec_locator/api/demo.html

# 方式2：通过HTTP服务器
cd spec_locator/api
python -m http.server 8080
# 访问 http://localhost:8080/demo.html
```

#### **技术栈**
- 纯原生实现（HTML5 + CSS3 + JavaScript）
- 无需任何框架或依赖
- 使用现代Web API（Fetch、FormData、FileReader、Drag & Drop）

---

### 3. CORS跨域支持

#### **功能描述**
添加了CORS中间件，允许前端页面跨域访问API。

#### **实现细节**
修改 `api/server.py`：
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### **生产环境配置**
```python
# 限制允许的源
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://api.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
```

---

### 4. OCR引擎兼容性修复

#### **问题描述**
PaddlePaddle 3.x的PIR（Program Intermediate Representation）与OneDNN/MKL-DNN优化不兼容，导致OCR识别失败。

#### **解决方案**
修改 `ocr/ocr_engine.py` 中的初始化参数：
```python
self.recognizer = PaddleOCR(
    use_angle_cls=True,
    lang="ch",
    device='cpu',
    enable_mkldnn=False,  # 禁用OneDNN优化
    use_mp=False,         # 禁用多进程
)
```

#### **版本降级**
为确保稳定性，推荐使用以下版本组合：
- PaddlePaddle: 2.6.2（从3.3.0降级）
- PaddleOCR: 2.8.1（从3.3.2降级）
- NumPy: 1.26.4（从2.2.6降级）

#### **安装命令**
```bash
pip install paddlepaddle==2.6.2 paddleocr==2.8.1 numpy==1.26.4
```

---

### 5. 文档更新

#### **新增文档**
1. **FRONTEND_INTEGRATION_GUIDE.md** - 前端集成与API调用详解
   - 系统架构说明
   - API调用完整流程
   - 多语言客户端示例
   - 关键技术点解析

2. **DEPLOYMENT_GUIDE.md** - 部署与API集成指南
   - 团队API服务提供方案
   - Docker容器化配置
   - AWS云服务器部署（EC2、ECS、Elastic Beanstalk）
   - 生产环境配置与监控
   - 多语言客户端SDK示例

3. **DEMO_USAGE.md** - 演示页面使用指南
   - 快速启动方式
   - API端点详细说明
   - 前端集成示例
   - 故障排查指南

#### **更新的文档**
- **readme.md** - 更新启动端口为8002，添加演示页面链接

---

### 6. 端口配置更新

#### **默认端口变更**
- 旧端口：8000
- 新端口：8002（避免常见端口冲突）

#### **启动方式**
```bash
# 激活环境
cd D:\projects\liuzong\spec_locator
.\.venv\Scripts\Activate.ps1

# 启动服务
cd ..
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002
```

#### **访问地址**
- API文档：http://127.0.0.1:8002/docs
- 演示页面：file:///D:/projects/liuzong/spec_locator/api/demo.html
- 健康检查：http://127.0.0.1:8002/health

---

### 7. 启动脚本优化

#### **新增文件**
- `start_demo.bat` - Windows批处理启动脚本
- `start_server.py` - Python跨平台启动脚本

#### **start_demo.bat 功能**
```batch
@echo off
# 1. 激活虚拟环境
# 2. 设置PYTHONPATH
# 3. 启动uvicorn服务器
# 4. 自动打开演示页面
```

#### **start_server.py 功能**
```python
# 1. 检查虚拟环境
# 2. 安装包（可编辑模式）
# 3. 启动服务器
# 4. 自动打开浏览器
```

---

## 升级指南

### 从旧版本升级

如果你使用的是旧版本（端口8000），请按以下步骤升级：

1. **停止旧服务**
```bash
# 停止运行在8000端口的服务
# Windows: Ctrl+C
# 或者查找并结束进程
```

2. **更新代码**
```bash
git pull origin main
```

3. **更新依赖**
```bash
# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 降级到稳定版本
pip install paddlepaddle==2.6.2 paddleocr==2.8.1 numpy==1.26.4
```

4. **启动新服务**
```bash
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002
```

5. **更新客户端配置**
如果有程序调用API，请将URL中的端口从8000改为8002：
```python
# 旧
API_URL = "http://127.0.0.1:8000/api/spec-locate"

# 新
API_URL = "http://127.0.0.1:8002/api/spec-locate"
```

---

## 向后兼容性

### API接口兼容性
✅ **完全兼容** - 所有旧版API端点保持不变
✅ **仅新增字段** - POST响应中新增 `file.download_url`，不影响旧客户端
✅ **可选功能** - 演示页面和CORS为可选功能，不影响核心API

### 不兼容变更
⚠️ **默认端口变更** - 从8000改为8002（需要更新客户端配置）
⚠️ **依赖版本降级** - PaddlePaddle 3.x → 2.6.2（提高稳定性）

---

## 性能对比

### OCR识别性能

| 版本 | PaddlePaddle | 识别准确率 | 平均耗时 | 稳定性 |
|------|-------------|-----------|---------|--------|
| v1.0.0 | 3.3.0 | ~85% | 2.5s | ⚠️ 不稳定 |
| v1.1.0 | 2.6.2 | ~88% | 2.3s | ✅ 稳定 |

### 功能对比

| 功能 | v1.0.0 | v1.1.0 |
|------|--------|--------|
| 规范识别 | ✅ | ✅ |
| 页码识别 | ✅ | ✅ |
| 文件索引 | ✅ | ✅ |
| 文件下载 | ✅ | ✅ |
| 下载URL | ❌ | ✅ 新增 |
| 演示界面 | ❌ | ✅ 新增 |
| CORS支持 | ❌ | ✅ 新增 |
| 部署文档 | ❌ | ✅ 新增 |

---

## 贡献指南

欢迎提交 Issue 和 PR！

## 许可证

MIT License

---

**联系方式**：hanyang.yin@example.com
