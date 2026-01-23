# 项目部署就绪检查报告

**检查日期：** 2026-01-23  
**项目：** Spec Locator Service

---

## ✅ 检查结果总览

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 1. 依赖配置文件 | ✅ **通过** | 有 pyproject.toml |
| 2. OCR 模型下载时机 | ⚠️ **需改进** | 会在实例化时下载 |
| 3. 索引目录环境变量配置 | ⚠️ **需改进** | 未使用环境变量 |
| 4. 统一启动方式 | ✅ **通过** | 可统一启动 |

---

## 详细检查结果

### 1. ✅ 依赖配置文件

**检查项：** 项目是否有 requirements.txt 或 pyproject.toml

**结果：** ✅ **通过**

**说明：**
- 存在 `pyproject.toml` 文件
- 已定义所有必要的依赖：
  - fastapi>=0.95.0
  - uvicorn[standard]>=0.20.0
  - paddleocr>=2.7.0
  - opencv-python>=4.6.0
  - numpy>=1.21.0
  - paddlepaddle>=3.1.1

**建议：**
创建 `requirements.txt` 以便于直接安装：
```bash
pip freeze > requirements.txt
```

或从 pyproject.toml 生成：
```bash
pip install .
pip freeze > requirements.txt
```

---

### 2. ⚠️ OCR 模型下载时机

**检查项：** OCR 模型不应在 import 时自动下载

**结果：** ⚠️ **需改进**

**当前问题：**
1. **实例化时自动下载**：OCREngine在 `__init__()` 中调用 `_initialize_ocr()`
2. **Pipeline自动初始化**：SpecLocatorPipeline 在初始化时创建 OCREngine
3. **API启动时初始化**：FastAPI应用启动时会实例化 pipeline

**代码位置：**

`ocr/ocr_engine.py:48-75`：
```python
def __init__(self, use_gpu: bool = False, conf_threshold: float = 0.3):
    self.use_gpu = use_gpu
    self.conf_threshold = conf_threshold
    self.recognizer = None
    self._initialize_ocr()  # ← 这里会触发模型下载

def _initialize_ocr(self):
    from paddleocr import PaddleOCR  # ← import时不会下载
    self.recognizer = PaddleOCR(...)  # ← 实例化时会下载模型
```

`api/server.py:35`：
```python
# 初始化流水线（在模块加载时）
pipeline = SpecLocatorPipeline()  # ← 导致OCR模型在启动时下载
```

**建议修复方案：**

#### 方案A：懒加载模式（推荐）

修改 `ocr/ocr_engine.py`：
```python
class OCREngine:
    def __init__(self, use_gpu: bool = False, conf_threshold: float = 0.3):
        self.use_gpu = use_gpu
        self.conf_threshold = conf_threshold
        self.recognizer = None
        # 不在初始化时加载，改为首次使用时加载

    def _initialize_ocr(self):
        """懒加载：仅在首次调用recognize时初始化"""
        if self.recognizer is not None:
            return
        
        from paddleocr import PaddleOCR
        logger.info("Initializing PaddleOCR (first use)...")
        # ... 初始化代码
    
    def recognize(self, image: np.ndarray):
        self._initialize_ocr()  # ← 首次使用时才初始化
        # ... 识别代码
```

#### 方案B：显式初始化方法

```python
class OCREngine:
    def __init__(self, use_gpu: bool = False, conf_threshold: float = 0.3):
        self.use_gpu = use_gpu
        self.conf_threshold = conf_threshold
        self.recognizer = None
        # 不自动初始化
    
    def initialize(self):
        """显式初始化方法"""
        self._initialize_ocr()
    
    def recognize(self, image: np.ndarray):
        if self.recognizer is None:
            raise RuntimeError("OCR engine not initialized. Call initialize() first.")
        # ... 识别代码
```

在 FastAPI 中使用 lifespan 事件：
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    logger.info("Initializing OCR engine...")
    pipeline.ocr_engine.initialize()
    yield
    # 关闭时（可选）

app = FastAPI(lifespan=lifespan)
```

**影响：**
- ⚠️ 首次API请求会稍慢（需要下载/加载模型）
- ✅ 容器启动更快
- ✅ CI/CD更友好
- ✅ 可以预先下载模型到容器镜像

---

### 3. ⚠️ 索引目录环境变量配置

**检查项：** 索引目录（PDF / metadata）路径可通过环境变量指定

**结果：** ⚠️ **需改进**

**当前实现：**

`database/file_index.py:30-38`：
```python
def __init__(self, data_dir: str = None):
    if data_dir is None:
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "output_pages"  # ← 硬编码相对路径
    
    self.data_dir = Path(data_dir)
```

**问题：**
- 默认路径是相对于代码位置计算的
- 没有从环境变量读取配置
- 不利于容器化部署和多环境配置

**建议修复：**

#### 步骤1：添加环境变量配置

修改 `config/config.py`：
```python
# ===== 数据目录配置 =====
class DataConfig:
    """数据目录配置"""
    # 默认值：相对于项目根目录
    DEFAULT_DATA_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..",
        "output_pages"
    )
    
    # 从环境变量读取，支持绝对路径或相对路径
    DATA_DIR = os.getenv("SPEC_DATA_DIR", DEFAULT_DATA_DIR)
    
    # 展开用户目录和相对路径
    DATA_DIR = os.path.abspath(os.path.expanduser(DATA_DIR))
```

#### 步骤2：修改 FileIndex

修改 `database/file_index.py`：
```python
from spec_locator.config import DataConfig

class FileIndex:
    def __init__(self, data_dir: str = None):
        """
        初始化文件索引

        Args:
            data_dir: 数据目录路径，默认从环境变量 SPEC_DATA_DIR 读取
        """
        if data_dir is None:
            data_dir = DataConfig.DATA_DIR
        
        self.data_dir = Path(data_dir)
        self.index: Dict[str, List[SpecFile]] = {}
        self._build_index()
```

#### 步骤3：使用示例

```bash
# Linux/Mac
export SPEC_DATA_DIR=/data/spec_pdfs
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002

# Windows
set SPEC_DATA_DIR=D:\data\spec_pdfs
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002

# Docker
docker run -e SPEC_DATA_DIR=/data \
  -v /host/pdfs:/data \
  spec-locator:latest

# Docker Compose
environment:
  - SPEC_DATA_DIR=/app/data
volumes:
  - ./output_pages:/app/data
```

---

### 4. ✅ 统一启动方式

**检查项：** 启动方式统一（如 uvicorn app.main:app）

**结果：** ✅ **通过**

**当前启动方式：**
```bash
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002
```

**符合标准：**
- ✅ 使用标准的 uvicorn 启动
- ✅ 模块路径清晰（spec_locator.api.server:app）
- ✅ 参数标准化

**建议：**

#### 创建启动入口文件（可选）

为了更简洁的启动命令，可以创建 `main.py`：

```python
# spec_locator/main.py
"""
应用入口文件
"""
from spec_locator.api.server import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    import os
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8002"))
    
    uvicorn.run(
        "spec_locator.main:app",
        host=host,
        port=port,
        reload=os.getenv("API_RELOAD", "false").lower() == "true"
    )
```

启动方式：
```bash
# 方式1：uvicorn命令
uvicorn spec_locator.main:app --host 0.0.0.0 --port 8002

# 方式2：Python直接运行
python -m spec_locator.main

# 方式3：更简洁（如果创建了main.py）
python main.py
```

---

## 🔧 修复优先级

| 优先级 | 检查项 | 影响 | 工作量 |
|--------|--------|------|--------|
| **P0（高）** | 索引目录环境变量 | 部署必需 | 小（30分钟） |
| **P1（中）** | OCR模型懒加载 | 改善启动体验 | 中（2小时） |
| **P2（低）** | 生成requirements.txt | 方便安装 | 小（5分钟） |

---

## 📋 完整修复清单

### 立即修复（部署前必须）

- [ ] **添加环境变量支持**
  - [ ] 修改 `config/config.py` 添加 DataConfig
  - [ ] 修改 `database/file_index.py` 使用环境变量
  - [ ] 更新文档说明环境变量用法

### 建议修复（提升体验）

- [ ] **OCR模型懒加载**
  - [ ] 修改 `ocr/ocr_engine.py` 实现懒加载
  - [ ] 修改 `api/server.py` 使用 lifespan 或懒加载
  - [ ] 添加健康检查端点显示模型状态

- [ ] **创建requirements.txt**
  - [ ] 运行 `pip freeze > requirements.txt`
  - [ ] 清理不必要的依赖

- [ ] **创建启动入口**
  - [ ] 创建 `spec_locator/main.py`
  - [ ] 更新启动文档

---

## 📦 Docker部署配置建议

基于检查结果，推荐的 Dockerfile：

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgomp1 libglib2.0-0 libsm6 libxext6 \
    libxrender-dev libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml /app/
COPY spec_locator/ /app/spec_locator/

# 安装Python依赖
RUN pip install --no-cache-dir \
    paddlepaddle==2.6.2 \
    paddleocr==2.8.1 \
    numpy==1.26.4 \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    opencv-python-headless

# 预下载OCR模型（可选，加速首次运行）
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='ch')"

# 环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV SPEC_DATA_DIR=/app/data

# 数据目录
VOLUME /app/data

EXPOSE 8002

# 启动命令
CMD ["uvicorn", "spec_locator.api.server:app", "--host", "0.0.0.0", "--port", "8002"]
```

Docker Compose 配置：

```yaml
version: '3.8'

services:
  spec-locator:
    build: .
    ports:
      - "8002:8002"
    environment:
      - SPEC_DATA_DIR=/app/data
      - OCR_USE_GPU=false
      - LOG_LEVEL=INFO
    volumes:
      - ./output_pages:/app/data:ro
      - ./logs:/app/logs
    restart: unless-stopped
```

---

## ✅ 部署前检查清单

在部署到生产环境前，确保完成以下检查：

### 环境配置
- [ ] 设置 `SPEC_DATA_DIR` 环境变量
- [ ] 确认 PDF 文件已上传到正确位置
- [ ] 检查目录权限（至少可读）

### 依赖安装
- [ ] 安装所有依赖（从 pyproject.toml 或 requirements.txt）
- [ ] 验证 PaddlePaddle 和 PaddleOCR 版本兼容性
- [ ] 测试 OCR 模型可以正常下载

### 服务配置
- [ ] 配置正确的端口（默认8002）
- [ ] 设置日志级别
- [ ] 配置文件上传大小限制
- [ ] 如需要，配置 CORS 允许的域名

### 测试验证
- [ ] 健康检查端点正常：`GET /health`
- [ ] 上传测试图片能正常识别
- [ ] 文件索引正确加载
- [ ] 下载功能正常工作

---

## 📚 相关文档

- [部署指南](DEPLOYMENT_GUIDE.md) - 完整的部署流程
- [前端集成指南](FRONTEND_INTEGRATION_GUIDE.md) - API调用说明
- [开发文档](README_DEV.md) - 开发者参考

---

**生成时间：** 2026-01-23  
**检查工具版本：** 1.0.0
