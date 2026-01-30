# Spec Locator Service - Docker 部署指南

## 📦 概述

本项目已完成 Docker 化，提供单容器方案，包含：
- ✅ PaddleOCR 模型预下载
- ✅ **LLM 视觉模型集成**（支持豆包/OpenAI/Gemini）
- ✅ **OCR + LLM 混合识别模式**
- ✅ FastAPI 规范定位服务
- ✅ Volume 挂载外部数据
- ✅ 健康检查和自动重启（`restart: always`）
- ✅ **OCR 启动预热**（避免首次请求 30 秒卡顿）
- ✅ 资源限制和日志管理

---

## 🔧 关键特性

### 1. **容器自动重启**
- 配置 `restart: always` 确保容器异常退出后自动重启
- 适用于：崩溃、OOM、Docker 重启等场景

### 2. **OCR 启动预热**
- `OCR_WARMUP_ON_STARTUP=true` 在应用启动时后台预热 OCR 模型
- 避免"首次请求时临时初始化导致 30 秒超时"
- 预热在后台线程执行，不阻塞服务启动

---

## 🚀 快速启动

### 前置要求

1. **安装 Docker 和 Docker Compose**
   - Docker: https://docs.docker.com/get-docker/
   - Docker Compose: https://docs.docker.com/compose/install/

2. **准备数据目录**
   ```bash
   # 确保 output_pages 目录存在且包含 PDF 文件
   dir output_pages
   
   # 自动创建工作目录（如不存在）
   mkdir -p spec_locator/uploads spec_locator/logs spec_locator/temp
   ```

### 启动服务

#### 方法 1：使用 Docker Compose（推荐）

```bash
# 构建镜像
docker-compose build

# 启动服务（后台运行）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 方法 2：使用 Docker 命令

```bash
# 构建镜像
docker build -t spec-locator:1.0.0 .

# 运行容器
docker run -d \
  --name spec-locator \
  -p 8002:8002 \
  -v ${PWD}/output_pages:/app/data/output_pages:ro \
  -v ${PWD}/spec_locator/uploads:/app/uploads:rw \
  -v ${PWD}/spec_locator/logs:/app/logs:rw \
  -v ${PWD}/spec_locator/temp:/app/temp:rw \
  -e SPEC_DATA_DIR=/app/data/output_pages \
  -e OCR_USE_GPU=false \
  spec-locator:1.0.0

# 查看日志
docker logs -f spec-locator

# 停止容器
docker stop spec-locator
docker rm spec-locator
```

---

## 🌐 访问服务

启动成功后，可通过以下地址访问：

- **API 文档**: http://localhost:8002/docs
- **健康检查**: http://localhost:8002/health
- **演示页面**: 在浏览器打开 `file:///path/to/spec_locator/api/demo.html`

---

## 📁 目录结构

### 宿主机目录

```
D:\projects\liuzong\
├── output_pages/              # PDF 数据（只读挂载）
├── spec_locator/
│   ├── uploads/               # 上传文件（读写）
│   ├── logs/                  # 日志文件（读写）
│   └── temp/                  # 临时文件（读写）
├── Dockerfile
├── docker-compose.yml
└── .env.docker
```

### 容器内目录

```
/app/
├── data/
│   └── output_pages/         -> 宿主机 ./output_pages
├── uploads/                  -> 宿主机 ./spec_locator/uploads
├── logs/                     -> 宿主机 ./spec_locator/logs
├── temp/                     -> 宿主机 ./spec_locator/temp
└── spec_locator/             # 应用代码
```

---

## ⚙️ 配置说明

### 环境变量

主要环境变量在 `docker-compose.yml` 中配置：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SPEC_DATA_DIR` | `/app/data/output_pages` | PDF 文件目录 |
| `API_PORT` | `8002` | API 服务端口 |
| `OCR_USE_GPU` | `false` | 是否使用 GPU |
| `OCR_LAZY_LOAD` | `true` | OCR 懒加载 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

### 修改配置

1. 编辑 `docker-compose.yml` 中的 `environment` 部分
2. 或使用 `.env` 文件（创建项目根目录下的 `.env`）

```bash
# .env 文件示例
SPEC_DATA_DIR=/app/data/output_pages
OCR_USE_GPU=false
LOG_LEVEL=DEBUG
```

---

## 🔧 常用命令

### 查看服务状态

```bash
# 查看运行中的容器
docker-compose ps

# 查看服务健康状态
curl http://localhost:8002/health
```

### 查看日志

```bash
# 实时日志
docker-compose logs -f

# 最近 100 行日志
docker-compose logs --tail=100

# 查看特定服务日志
docker-compose logs -f spec-locator
```

### 进入容器调试

```bash
# 进入容器 shell
docker-compose exec spec-locator /bin/bash

# 以 root 用户进入
docker-compose exec -u root spec-locator /bin/bash

# 查看容器内进程
docker-compose exec spec-locator ps aux

# 查看容器内目录
docker-compose exec spec-locator ls -la /app/data/output_pages
```

### 重启服务

```bash
# 重启服务
docker-compose restart

# 重新构建并启动
docker-compose up -d --build

# 完全清理并重启
docker-compose down
docker-compose up -d --build
```

### 清理资源

```bash
# 停止并删除容器
docker-compose down

# 停止并删除容器、镜像
docker-compose down --rmi all

# 停止并删除容器、Volume
docker-compose down -v

# 清理悬空镜像
docker image prune -f

# 清理所有未使用的资源
docker system prune -af
```

---

## 🐛 故障排查

### 问题 1：容器无法启动

**症状**: `docker-compose up` 失败

**解决方法**:
```bash
# 查看详细日志
docker-compose logs spec-locator

# 检查端口占用
netstat -ano | findstr :8002

# 检查 Volume 挂载路径是否存在
dir output_pages
```

### 问题 2：无法访问 output_pages 文件

**症状**: API 返回 "文件未找到"

**解决方法**:
```bash
# 检查容器内路径
docker-compose exec spec-locator ls -la /app/data/output_pages

# 检查环境变量
docker-compose exec spec-locator env | grep SPEC_DATA_DIR

# 检查宿主机路径
dir output_pages
```

### 问题 3：OCR 识别失败或首次请求卡顿

**症状**: OCR 返回错误、空结果或首次请求超时 30 秒

**解决方法**:

#### 3.1 验证 OCR 预热是否生效
```bash
# 查看容器日志，应该看到 "后台预热 OCR 模型..." 和 "✓ OCR 模型预热完成"
docker logs spec-locator | grep -E "预热|OCR"

# 如果没有看到预热日志，检查环境变量
docker exec spec-locator env | grep OCR_WARMUP_ON_STARTUP
# 应该输出: OCR_WARMUP_ON_STARTUP=true
```

#### 3.2 检查 PaddleOCR 模型下载
```bash
# 检查 PaddleOCR 模型是否下载
docker exec spec-locator ls -la /home/appuser/.paddleocr/whl/

# 如果模型未下载，可能是网络问题
docker logs spec-locator | grep "paddleocr.bj.bcebos.com"
```

#### 3.3 网络问题导致模型下载失败
```bash
# 症状：日志显示 "Failed to resolve 'paddleocr.bj.bcebos.com'"
# 解决方法：配置 DNS 或使用代理

# 方法1：在 docker-compose.yml 中添加 DNS
services:
  spec-locator:
    dns:
      - 8.8.8.8
      - 114.114.114.114

# 方法2：在宿主机预下载模型，然后挂载到容器
# 1. 在宿主机运行 Python 下载模型
python -c "from paddleocr import PaddleOCR; PaddleOCR()"

# 2. 在 docker-compose.yml 中挂载模型目录
volumes:
  - ~/.paddleocr:/home/appuser/.paddleocr:ro
```

#### 3.4 手动测试 OCR
```bash
docker exec spec-locator python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR()"
```

### 问题 4：内存不足

**症状**: 容器 OOM (Out of Memory)

**解决方法**:
```bash
# 修改 docker-compose.yml 中的内存限制
deploy:
  resources:
    limits:
      memory: 4G  # 增加到 4GB

# 重启服务
docker-compose down
docker-compose up -d
```

### 问题 5：日志文件无法写入

**症状**: 日志文件权限错误

**解决方法**:
```bash
# 检查宿主机目录权限
icacls spec_locator\logs

# 在容器内检查权限
docker-compose exec spec-locator ls -la /app/logs

# 修改宿主机目录权限（Windows）
icacls spec_locator\logs /grant Everyone:F
```

---

## 🚀 性能优化

### 1. 启用 OCR 预热

在 `docker-compose.yml` 中设置：
```yaml
environment:
  - OCR_WARMUP_ON_STARTUP=true
```

### 2. 增加工作进程

```yaml
environment:
  - API_WORKERS=4  # 根据 CPU 核心数调整
```

### 3. 使用 GPU 加速（可选）

需要安装 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

修改 `docker-compose.yml`：
```yaml
spec-locator:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  environment:
    - OCR_USE_GPU=true
```

修改 `Dockerfile`，使用 CUDA 基础镜像：
```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
# ... 安装 Python 3.10
```

---

## 🔐 安全建议

### 生产环境部署

1. **使用非 root 用户**: 已在 Dockerfile 中配置 `appuser`
2. **设置资源限制**: 已在 docker-compose.yml 中配置
3. **只读挂载数据**: `output_pages` 使用 `:ro` 标志
4. **定期更新镜像**: `docker-compose pull` 和 `docker-compose up -d`
5. **使用 HTTPS**: 配置 Nginx 反向代理

### 日志管理

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"   # 单个日志文件最大 10MB
    max-file: "3"     # 保留最近 3 个日志文件
```

---

## 📊 监控和运维

### 资源监控

```bash
# 查看容器资源使用
docker stats spec-locator

# 实时监控
docker stats --no-stream
```

### 备份和恢复

```bash
# 备份 uploads 目录
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz spec_locator/uploads

# 备份日志
tar -czf logs_backup_$(date +%Y%m%d).tar.gz spec_locator/logs

# 恢复
tar -xzf uploads_backup_20260123.tar.gz
```

---

## 📝 更新日志

### v1.1.0 (2026-01-30)
- ✅ **新增 LLM 视觉模型集成**（支持豆包/OpenAI/Gemini）
- ✅ **OCR + LLM 混合识别模式**
- ✅ 自动降级机制（LLM 失败时回退到 OCR）
- ✅ 支持多种大模型提供商配置

### v1.0.0 (2026-01-23)
- ✅ 初始 Docker 化版本
- ✅ 单容器方案
- ✅ PaddleOCR 模型预下载
- ✅ Volume 挂载支持
- ✅ 健康检查和自动重启
- ✅ 资源限制和日志管理

---

## 🆘 获取帮助

- **查看 API 文档**: http://localhost:8002/docs
- **查看项目文档**: [readme.md](readme.md)
- **报告问题**: 联系项目维护者

---

## 📄 许可证

MIT License
