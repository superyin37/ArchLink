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

## 贡献指南

欢迎提交 Issue 和 PR！

## 许可证

MIT License

---

**联系方式**：hanyang.yin@example.com
