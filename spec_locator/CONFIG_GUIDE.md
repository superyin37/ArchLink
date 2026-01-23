# 环境变量配置指南

## 概述

Spec Locator Service 支持通过环境变量进行灵活配置，解决了硬编码路径的问题，使项目在不同环境（开发、测试、生产）下更易于部署和维护。

## 配置方式优先级

配置读取优先级（从高到低）：
1. 系统环境变量
2. `.env` 文件
3. 代码中的默认值

## 主要环境变量

### 数据目录配置

#### `SPEC_DATA_DIR` (重要)
- **说明**: 规范文件索引目录，包含所有PDF文件
- **默认值**: `../output_pages` (相对于项目根目录)
- **示例**: `D:\projects\liuzong\output_pages`
- **注意**: 必须确保该目录存在且可访问，否则文件查找功能将不可用

#### `SPEC_UPLOAD_DIR`
- **说明**: 上传文件临时存储目录
- **默认值**: `./uploads` (相对于 spec_locator 目录)
- **示例**: `D:\projects\liuzong\spec_locator\uploads`

#### `SPEC_TEMP_DIR`
- **说明**: 临时文件目录
- **默认值**: `./temp`
- **示例**: `D:\projects\liuzong\spec_locator\temp`

#### `SPEC_LOG_DIR`
- **说明**: 日志文件存储目录
- **默认值**: `./logs`
- **示例**: `D:\projects\liuzong\spec_locator\logs`

### API 服务配置

#### `API_HOST`
- **说明**: API 服务监听地址
- **默认值**: `0.0.0.0`
- **可选值**: `127.0.0.1` (仅本地), `0.0.0.0` (所有接口)

#### `API_PORT`
- **说明**: API 服务端口
- **默认值**: `8000`
- **示例**: `8002`

#### `API_WORKERS`
- **说明**: Uvicorn 工作进程数
- **默认值**: `4`

### 日志配置

#### `LOG_LEVEL`
- **说明**: 日志级别
- **默认值**: `INFO`
- **可选值**: `DEBUG`, `INFO`, `WARNING`, `ERROR`

#### `DEBUG`
- **说明**: 调试模式开关
- **默认值**: `false`
- **可选值**: `true`, `false`

### OCR 配置

#### `OCR_USE_GPU`
- **说明**: 是否使用 GPU 进行 OCR
- **默认值**: `false`
- **可选值**: `true`, `false`

#### `OCR_PRECISION`
- **说明**: OCR 精度
- **默认值**: `fp32`
- **可选值**: `fp32`, `fp16`

#### `OCR_CONF_THRESHOLD`
- **说明**: OCR 置信度阈值
- **默认值**: `0.3`
- **范围**: `0.0` - `1.0`

## 配置方法

### 方法1：使用 .env 文件（推荐开发环境）

1. 复制示例文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件：
```bash
# 数据目录配置
SPEC_DATA_DIR=D:\projects\liuzong\output_pages

# API 配置
API_PORT=8002
LOG_LEVEL=DEBUG
DEBUG=true
```

3. 启动服务（会自动加载 .env）：
```bash
start_demo.bat
```

### 方法2：在启动脚本中设置（推荐）

编辑 `start_demo.bat`:
```bat
@echo off
echo 设置环境变量...
set SPEC_DATA_DIR=D:\projects\liuzong\output_pages
set API_PORT=8002
set LOG_LEVEL=INFO

echo 启动服务...
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port %API_PORT%
```

### 方法3：PowerShell 临时设置

```powershell
# 当前会话
$env:SPEC_DATA_DIR="D:\projects\liuzong\output_pages"
$env:API_PORT=8002

# 启动服务
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002
```

### 方法4：系统环境变量（推荐生产环境）

**Windows (用户级别):**
```powershell
[Environment]::SetEnvironmentVariable("SPEC_DATA_DIR", "D:\projects\liuzong\output_pages", "User")
```

**Windows (系统级别，需管理员权限):**
```powershell
[Environment]::SetEnvironmentVariable("SPEC_DATA_DIR", "D:\projects\liuzong\output_pages", "Machine")
```

**或通过图形界面:**
1. 右键"此电脑" → "属性"
2. "高级系统设置" → "环境变量"
3. 添加新变量

### 方法5：Docker 容器

```dockerfile
FROM python:3.10

# 设置环境变量
ENV SPEC_DATA_DIR=/data/output_pages
ENV API_PORT=8000
ENV LOG_LEVEL=INFO

WORKDIR /app
COPY . .
RUN pip install -e .

CMD ["uvicorn", "spec_locator.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

或使用 docker-compose.yml:
```yaml
version: '3.8'
services:
  spec-locator:
    build: .
    environment:
      SPEC_DATA_DIR: /data/output_pages
      API_PORT: 8000
      LOG_LEVEL: INFO
    volumes:
      - ./output_pages:/data/output_pages
    ports:
      - "8000:8000"
```

## 验证配置

### 检查环境变量
```python
from spec_locator.config import PathConfig

print(f"数据目录: {PathConfig.SPEC_DATA_DIR}")
print(f"上传目录: {PathConfig.UPLOAD_DIR}")
print(f"日志目录: {PathConfig.LOG_DIR}")
```

### 验证数据目录
```python
from spec_locator.config import PathConfig

try:
    PathConfig.validate_data_dir()
    print("✓ 数据目录验证通过")
except FileNotFoundError as e:
    print(f"✗ 数据目录不存在: {e}")
except NotADirectoryError as e:
    print(f"✗ 路径不是目录: {e}")
```

### 测试完整功能
```bash
cd D:\projects\liuzong
python spec_locator\test_file_index.py
```

## 常见问题

### Q1: 数据目录不存在怎么办？
**A**: 确保 `SPEC_DATA_DIR` 指向的目录存在：
```bash
mkdir D:\projects\liuzong\output_pages
```

### Q2: .env 文件不生效？
**A**: 检查：
1. `.env` 文件是否在 `spec_locator/` 目录下
2. 是否安装了 `python-dotenv`: `pip install python-dotenv`
3. 重启服务以重新加载配置

### Q3: 如何切换不同的数据目录？
**A**: 三种方式：
1. 修改 `.env` 文件中的 `SPEC_DATA_DIR`
2. 临时设置: `set SPEC_DATA_DIR=新路径`
3. 在代码中传参: `FileIndex(data_dir="新路径")`

### Q4: 生产环境推荐配置？
**A**: 
```bash
SPEC_DATA_DIR=/data/spec/output_pages  # 使用绝对路径
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=8
LOG_LEVEL=WARNING
DEBUG=false
OCR_USE_GPU=true  # 如有GPU
```

## 最佳实践

1. **开发环境**: 使用 `.env` 文件，方便修改和测试
2. **测试环境**: 使用启动脚本设置，保证一致性
3. **生产环境**: 使用系统环境变量或容器环境变量，提高安全性
4. **团队协作**: 提交 `.env.example`，忽略 `.env`，避免配置冲突
5. **敏感信息**: 不要将包含敏感信息的 `.env` 提交到版本控制

## 安全注意事项

1. 将 `.env` 添加到 `.gitignore`，避免泄露配置
2. 生产环境避免使用 `DEBUG=true`
3. API_HOST 根据需求设置（`127.0.0.1` 更安全）
4. 定期审查日志文件权限
5. 数据目录设置适当的文件系统权限

## 迁移指南

### 从硬编码路径迁移

旧代码:
```python
data_dir = "../output_pages"  # 硬编码
```

新代码:
```python
from spec_locator.config import PathConfig
data_dir = PathConfig.SPEC_DATA_DIR  # 使用配置
```

### 无需修改现有代码

由于提供了合理的默认值，现有代码无需修改即可工作。但建议设置 `.env` 文件以便于管理。

## 更多信息

- 查看所有配置项: `spec_locator/config/config.py`
- 配置模板: `.env.example`
- 问题反馈: GitHub Issues
