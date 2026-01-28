# =============================================================================
# Spec Locator Service - Docker Image
# =============================================================================
# 基于 Python 3.10 的单容器方案
# 包含 PaddleOCR + FastAPI + 规范定位识别服务

FROM python:3.10-slim

# 设置维护者信息
LABEL maintainer="Yin Hanyang <hanyang.yin@example.com>"
LABEL description="CAD 截图规范定位识别服务"
LABEL version="1.0.0"

# =============================================================================
# 系统环境配置
# =============================================================================

# 设置环境变量（避免 Python 缓冲和字节码生成）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Asia/Shanghai

# 设置工作目录
WORKDIR /app

# =============================================================================
# 安装系统依赖
# =============================================================================
# OpenCV 和 PaddlePaddle 需要的系统库

RUN apt-get update && apt-get install -y --no-install-recommends \
    # OpenCV 依赖（新版 Debian 使用 libgl1 替代 libgl1-mesa-glx）
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # 网络工具（健康检查）
    curl \
    # 清理缓存
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# =============================================================================
# 安装 Python 依赖
# =============================================================================

# 先复制依赖文件（利用 Docker 缓存层）
COPY spec_locator/requirements.txt /app/requirements.txt

# 安装 Python 包（使用清华镜像加速）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r /app/requirements.txt

# =============================================================================
# 预下载 PaddleOCR 模型（关键优化）
# =============================================================================
# 注意：由于 PaddlePaddle 在某些 Docker 环境中可能出现段错误
# 我们跳过预下载，改为首次运行时自动下载（懒加载）
# 如果需要预下载，建议在容器启动后手动执行

# 创建模型缓存目录
RUN mkdir -p /root/.paddleocr

# =============================================================================
# 复制应用代码
# =============================================================================

# 复制 spec_locator 目录
COPY spec_locator/ /app/spec_locator/

# 创建必要的工作目录
RUN mkdir -p /app/uploads \
    /app/temp \
    /app/logs \
    /app/data/output_pages

# =============================================================================
# 设置权限和用户
# =============================================================================
# 安全最佳实践：使用非 root 用户运行

# 创建非特权用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 切换到非特权用户
USER appuser

# =============================================================================
# 暴露端口
# =============================================================================

EXPOSE 8002

# =============================================================================
# 健康检查
# =============================================================================

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# =============================================================================
# 启动命令
# =============================================================================

# 使用 uvicorn 启动 FastAPI 应用
CMD ["uvicorn", "spec_locator.api.server:app", \
     "--host", "0.0.0.0", \
     "--port", "8002", \
     "--workers", "1", \
     "--log-level", "info"]
