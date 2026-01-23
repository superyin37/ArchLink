# 部署与API集成指南

本文档详细说明如何将规范定位识别系统部署到生产环境，以及如何为团队提供API服务。

---

## 📋 目录

1. [为团队提供API服务](#为团队提供api服务)
2. [Docker容器化部署](#docker容器化部署)
3. [AWS云服务器部署](#aws云服务器部署)
4. [生产环境配置](#生产环境配置)
5. [监控与维护](#监控与维护)

---

## 为团队提供API服务

### 1. API文档准备

#### **创建API规格文档**

FastAPI自动生成OpenAPI规格，团队可以通过以下方式访问：

```bash
# 启动服务后访问
http://your-server:8002/docs          # Swagger UI
http://your-server:8002/redoc         # ReDoc UI
http://your-server:8002/openapi.json  # OpenAPI JSON规格
```

#### **导出API文档**

```python
# 创建 export_api_spec.py
import json
from spec_locator.api.server import app

# 导出OpenAPI规格
with open("api_spec.json", "w", encoding="utf-8") as f:
    json.dump(app.openapi(), f, indent=2, ensure_ascii=False)

print("API规格已导出到 api_spec.json")
```

运行导出：
```bash
python export_api_spec.py
```

---

### 2. 客户端SDK示例

#### **Python客户端**

创建 `client_sdk.py`：

```python
"""
规范定位识别API - Python客户端SDK
"""
import requests
from typing import Optional, Dict, Any
from pathlib import Path

class SpecLocatorClient:
    """规范定位识别客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        """
        初始化客户端
        
        Args:
            base_url: API服务器地址
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            服务状态信息
        """
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def recognize(self, image_path: str) -> Dict[str, Any]:
        """
        识别CAD截图中的规范编号和页码
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            识别结果，包含规范编号、页码、置信度等
            
        Example:
            >>> client = SpecLocatorClient("http://api.example.com")
            >>> result = client.recognize("cad_screenshot.png")
            >>> print(f"规范: {result['spec']['code']}, 页码: {result['spec']['page']}")
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        with open(image_path, 'rb') as f:
            files = {'file': (image_path.name, f, 'image/png')}
            response = self.session.post(
                f"{self.base_url}/api/spec-locate",
                files=files,
                timeout=30
            )
        
        response.raise_for_status()
        return response.json()
    
    def download_pdf(self, spec_code: str, page_code: str, 
                     save_path: Optional[str] = None) -> str:
        """
        下载PDF文件
        
        Args:
            spec_code: 规范编号（如 "12J2"）
            page_code: 页码（如 "C11"）
            save_path: 保存路径（可选）
            
        Returns:
            保存的文件路径
        """
        response = self.session.get(
            f"{self.base_url}/api/download/{spec_code}/{page_code}",
            stream=True,
            timeout=30
        )
        response.raise_for_status()
        
        # 从响应头获取文件名
        if save_path is None:
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                save_path = content_disposition.split('filename=')[1].strip('"')
            else:
                save_path = f"{spec_code}_{page_code}.pdf"
        
        # 保存文件
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return save_path


# 使用示例
if __name__ == "__main__":
    # 1. 创建客户端
    client = SpecLocatorClient("http://your-server:8002")
    
    # 2. 健康检查
    try:
        health = client.health_check()
        print(f"✅ 服务正常: {health}")
    except Exception as e:
        print(f"❌ 服务异常: {e}")
        exit(1)
    
    # 3. 识别图片
    result = client.recognize("path/to/cad_screenshot.png")
    
    if result['success']:
        spec = result['spec']
        print(f"✅ 识别成功:")
        print(f"   规范编号: {spec['code']}")
        print(f"   页码: {spec['page']}")
        print(f"   置信度: {spec['confidence']:.2%}")
        
        # 4. 如果找到文件，下载PDF
        if result.get('file'):
            pdf_path = client.download_pdf(spec['code'], spec['page'])
            print(f"✅ PDF已下载: {pdf_path}")
        else:
            print("⚠️  未找到对应的PDF文件")
    else:
        print(f"❌ 识别失败: {result.get('message')}")
```

#### **JavaScript/Node.js客户端**

创建 `client_sdk.js`：

```javascript
/**
 * 规范定位识别API - JavaScript客户端SDK
 */
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');

class SpecLocatorClient {
    constructor(baseUrl = 'http://localhost:8002') {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.client = axios.create({
            baseURL: this.baseUrl,
            timeout: 30000
        });
    }

    /**
     * 健康检查
     */
    async healthCheck() {
        const response = await this.client.get('/health');
        return response.data;
    }

    /**
     * 识别CAD截图
     * @param {string} imagePath - 图片文件路径
     * @returns {Promise<Object>} 识别结果
     */
    async recognize(imagePath) {
        const formData = new FormData();
        formData.append('file', fs.createReadStream(imagePath));

        const response = await this.client.post('/api/spec-locate', formData, {
            headers: formData.getHeaders()
        });

        return response.data;
    }

    /**
     * 下载PDF文件
     * @param {string} specCode - 规范编号
     * @param {string} pageCode - 页码
     * @param {string} savePath - 保存路径
     */
    async downloadPdf(specCode, pageCode, savePath) {
        const response = await this.client.get(
            `/api/download/${specCode}/${pageCode}`,
            { responseType: 'stream' }
        );

        const writer = fs.createWriteStream(savePath);
        response.data.pipe(writer);

        return new Promise((resolve, reject) => {
            writer.on('finish', () => resolve(savePath));
            writer.on('error', reject);
        });
    }
}

// 使用示例
async function main() {
    const client = new SpecLocatorClient('http://your-server:8002');

    try {
        // 1. 健康检查
        const health = await client.healthCheck();
        console.log('✅ 服务正常:', health);

        // 2. 识别图片
        const result = await client.recognize('path/to/cad_screenshot.png');

        if (result.success) {
            const { spec } = result;
            console.log('✅ 识别成功:');
            console.log(`   规范编号: ${spec.code}`);
            console.log(`   页码: ${spec.page}`);
            console.log(`   置信度: ${(spec.confidence * 100).toFixed(1)}%`);

            // 3. 下载PDF
            if (result.file) {
                const pdfPath = await client.downloadPdf(
                    spec.code, 
                    spec.page, 
                    'output.pdf'
                );
                console.log(`✅ PDF已下载: ${pdfPath}`);
            }
        } else {
            console.log('❌ 识别失败:', result.message);
        }
    } catch (error) {
        console.error('❌ 错误:', error.message);
    }
}

module.exports = SpecLocatorClient;
```

#### **curl示例**

```bash
#!/bin/bash
# 示例：使用curl调用API

API_URL="http://your-server:8002"

# 1. 健康检查
echo "=== 健康检查 ==="
curl -X GET "$API_URL/health" | jq

# 2. 识别图片
echo -e "\n=== 识别图片 ==="
RESULT=$(curl -X POST "$API_URL/api/spec-locate" \
    -H "accept: application/json" \
    -F "file=@cad_screenshot.png")

echo $RESULT | jq

# 3. 提取规范和页码
SPEC_CODE=$(echo $RESULT | jq -r '.spec.code')
PAGE_CODE=$(echo $RESULT | jq -r '.spec.page')

echo "规范编号: $SPEC_CODE"
echo "页码: $PAGE_CODE"

# 4. 下载PDF
if [ "$SPEC_CODE" != "null" ]; then
    echo -e "\n=== 下载PDF ==="
    curl -X GET "$API_URL/api/download/$SPEC_CODE/$PAGE_CODE" \
        -o "${SPEC_CODE}_${PAGE_CODE}.pdf"
    echo "PDF已下载"
fi
```

---

### 3. API认证与安全

#### **添加API Key认证**

修改 `api/server.py`：

```python
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

# API Key配置
API_KEY = "your-secret-api-key-here"  # 生产环境应从环境变量读取
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """验证API Key"""
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return api_key

# 在需要保护的端点添加依赖
@app.post("/api/spec-locate", dependencies=[Depends(verify_api_key)])
async def locate_spec(file: UploadFile = File(...)):
    # ... 原有代码
```

**客户端使用：**
```python
# Python
headers = {"X-API-Key": "your-secret-api-key-here"}
response = requests.post(url, files=files, headers=headers)

# JavaScript
axios.post(url, formData, {
    headers: {
        'X-API-Key': 'your-secret-api-key-here'
    }
});

# curl
curl -H "X-API-Key: your-secret-api-key-here" ...
```

---

## Docker容器化部署

### 1. 创建Dockerfile

创建 `Dockerfile`：

```dockerfile
# 使用官方Python运行时作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY spec_locator/ /app/spec_locator/
COPY output_pages/ /app/output_pages/
COPY pyproject.toml /app/
COPY README.md /app/

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    paddlepaddle==2.6.2 \
    paddleocr==2.8.1 \
    numpy==1.26.4 \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    opencv-python-headless

# 暴露端口
EXPOSE 8002

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 启动命令
CMD ["uvicorn", "spec_locator.api.server:app", "--host", "0.0.0.0", "--port", "8002"]
```

### 2. 创建.dockerignore

创建 `.dockerignore`：

```
.git
.venv
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
.coverage
htmlcov
dist
build
*.egg-info
.DS_Store
logs/
temp/
uploads/
*.log
.env
```

### 3. 构建和运行

```bash
# 构建Docker镜像
docker build -t spec-locator:latest .

# 运行容器
docker run -d \
    --name spec-locator \
    -p 8002:8002 \
    -v $(pwd)/output_pages:/app/output_pages \
    spec-locator:latest

# 查看日志
docker logs -f spec-locator

# 停止容器
docker stop spec-locator

# 删除容器
docker rm spec-locator
```

### 4. Docker Compose配置

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  spec-locator:
    build: .
    container_name: spec-locator-api
    ports:
      - "8002:8002"
    volumes:
      - ./output_pages:/app/output_pages:ro
      - ./logs:/app/logs
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # 可选：Nginx反向代理
  nginx:
    image: nginx:alpine
    container_name: spec-locator-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - spec-locator
    restart: unless-stopped
```

**启动服务：**
```bash
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## AWS云服务器部署

### 方案1：EC2实例部署

#### **1. 创建EC2实例**

```bash
# AWS CLI创建实例
aws ec2 run-instances \
    --image-id ami-xxxxxxxxx \
    --instance-type t3.medium \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxxxxx \
    --subnet-id subnet-xxxxxxxxx \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=spec-locator-server}]'
```

**推荐配置：**
- **实例类型：** t3.medium (2 vCPU, 4GB RAM) 或 t3.large (2 vCPU, 8GB RAM)
- **存储：** 30GB gp3 SSD
- **操作系统：** Ubuntu 22.04 LTS
- **安全组：** 开放 22 (SSH), 8002 (API), 80/443 (HTTP/HTTPS)

#### **2. 连接并配置服务器**

```bash
# SSH连接
ssh -i your-key.pem ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com

# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### **3. 部署应用**

```bash
# 克隆代码（或上传压缩包）
git clone https://your-repo/spec-locator.git
cd spec-locator

# 上传PDF文件到output_pages目录
# 使用scp或AWS S3同步
aws s3 sync s3://your-bucket/output_pages ./output_pages

# 启动服务
docker-compose up -d

# 验证
curl http://localhost:8002/health
```

#### **4. 配置域名和SSL证书**

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取Let's Encrypt证书
sudo certbot --nginx -d api.yourdomain.com

# Nginx配置示例
sudo nano /etc/nginx/sites-available/spec-locator
```

**Nginx配置：**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 上传文件大小限制
    client_max_body_size 20M;

    location / {
        proxy_pass http://localhost:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/spec-locator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

### 方案2：AWS ECS (Elastic Container Service)

#### **1. 创建ECR仓库**

```bash
# 创建ECR仓库
aws ecr create-repository --repository-name spec-locator

# 获取登录令牌
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 构建并推送镜像
docker build -t spec-locator .
docker tag spec-locator:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/spec-locator:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/spec-locator:latest
```

#### **2. 创建ECS任务定义**

创建 `task-definition.json`：

```json
{
  "family": "spec-locator",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "spec-locator",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/spec-locator:latest",
      "portMappings": [
        {
          "containerPort": 8002,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "PYTHONUNBUFFERED",
          "value": "1"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/spec-locator",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### **3. 创建ECS服务**

```bash
# 注册任务定义
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 创建集群
aws ecs create-cluster --cluster-name spec-locator-cluster

# 创建服务
aws ecs create-service \
    --cluster spec-locator-cluster \
    --service-name spec-locator-service \
    --task-definition spec-locator \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

---

### 方案3：AWS Elastic Beanstalk

#### **1. 准备部署包**

创建 `Dockerrun.aws.json`：

```json
{
  "AWSEBDockerrunVersion": "1",
  "Image": {
    "Name": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/spec-locator:latest",
    "Update": "true"
  },
  "Ports": [
    {
      "ContainerPort": 8002
    }
  ]
}
```

#### **2. 部署到Elastic Beanstalk**

```bash
# 安装EB CLI
pip install awsebcli

# 初始化
eb init -p docker spec-locator-app --region us-east-1

# 创建环境并部署
eb create spec-locator-env --instance-type t3.medium

# 更新部署
eb deploy

# 查看状态
eb status

# 查看日志
eb logs
```

---

## 生产环境配置

### 1. 环境变量配置

创建 `.env` 文件：

```bash
# API配置
API_HOST=0.0.0.0
API_PORT=8002
API_KEY=your-secret-api-key-change-in-production

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/app/logs/api.log

# 数据目录
DATA_DIR=/app/output_pages

# OCR配置
OCR_USE_GPU=false
OCR_THRESHOLD=0.3

# 文件上传限制
MAX_UPLOAD_SIZE=20971520  # 20MB

# CORS配置
ALLOWED_ORIGINS=https://your-frontend.com,https://api.yourdomain.com
```

### 2. 配置管理

修改 `config/config.py`：

```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API配置
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8002"))
    api_key: str = os.getenv("API_KEY", "")
    
    # 数据目录
    data_dir: str = os.getenv("DATA_DIR", "../output_pages")
    
    # OCR配置
    ocr_use_gpu: bool = os.getenv("OCR_USE_GPU", "false").lower() == "true"
    ocr_threshold: float = float(os.getenv("OCR_THRESHOLD", "0.3"))
    
    # 文件上传
    max_upload_size: int = int(os.getenv("MAX_UPLOAD_SIZE", "20971520"))
    
    # CORS
    allowed_origins: list = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 3. 性能优化

#### **启用GPU加速（如有GPU）**

```dockerfile
# Dockerfile for GPU
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# ... 其他配置

# 安装GPU版本的PaddlePaddle
RUN pip install paddlepaddle-gpu==2.6.2
```

#### **使用Gunicorn+Uvicorn**

```bash
# 安装
pip install gunicorn

# 启动（多worker）
gunicorn spec_locator.api.server:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8002 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
```

#### **添加缓存（Redis）**

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
```

---

## 监控与维护

### 1. 日志监控

#### **配置日志**

```python
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
handler = RotatingFileHandler(
    "logs/api.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logging.getLogger().addHandler(handler)
```

#### **集成CloudWatch (AWS)**

```python
import watchtower

logger = logging.getLogger()
logger.addHandler(watchtower.CloudWatchLogHandler(
    log_group='/aws/ec2/spec-locator',
    stream_name='api-logs'
))
```

### 2. 健康检查

增强健康检查端点：

```python
@app.get("/health")
def health_check():
    """增强的健康检查"""
    stats = pipeline.file_index.get_stats()
    
    # 检查OCR引擎
    ocr_status = "ok" if pipeline.ocr_engine.recognizer else "error"
    
    # 检查磁盘空间
    import shutil
    disk_usage = shutil.disk_usage("/")
    disk_free_gb = disk_usage.free / (1024**3)
    
    return {
        "status": "ok" if ocr_status == "ok" else "degraded",
        "ocr_engine": ocr_status,
        "index_stats": stats,
        "disk_free_gb": round(disk_free_gb, 2),
        "timestamp": datetime.now().isoformat()
    }
```

### 3. 性能监控

使用Prometheus + Grafana：

```python
from prometheus_fastapi_instrumentator import Instrumentator

# 添加到FastAPI应用
Instrumentator().instrument(app).expose(app)
```

### 4. 自动化部署

创建 `deploy.sh`：

```bash
#!/bin/bash
set -e

echo "=== 规范定位识别系统 - 自动部署 ==="

# 1. 拉取最新代码
echo "[1/5] 拉取最新代码..."
git pull origin main

# 2. 构建Docker镜像
echo "[2/5] 构建Docker镜像..."
docker build -t spec-locator:latest .

# 3. 推送到ECR（如果使用AWS）
if [ -n "$AWS_ACCOUNT_ID" ]; then
    echo "[3/5] 推送到ECR..."
    docker tag spec-locator:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/spec-locator:latest
    docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/spec-locator:latest
fi

# 4. 停止旧容器
echo "[4/5] 停止旧容器..."
docker-compose down

# 5. 启动新容器
echo "[5/5] 启动新容器..."
docker-compose up -d

echo "✅ 部署完成！"
echo "服务地址: http://$(curl -s ifconfig.me):8002"
```

---

## 快速部署清单

### **本地测试 → 云服务器完整流程**

```bash
# 1. 本地测试
docker-compose up -d
curl http://localhost:8002/health

# 2. 配置AWS CLI
aws configure

# 3. 创建ECR并推送镜像
aws ecr create-repository --repository-name spec-locator
docker build -t spec-locator .
docker tag spec-locator:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/spec-locator:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/spec-locator:latest

# 4. 启动EC2实例
aws ec2 run-instances --image-id ami-xxx --instance-type t3.medium ...

# 5. SSH连接并部署
ssh -i key.pem ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com
git clone https://your-repo/spec-locator.git
cd spec-locator
docker-compose up -d

# 6. 配置域名和SSL
sudo certbot --nginx -d api.yourdomain.com

# 7. 测试API
curl https://api.yourdomain.com/health
```

---

## 团队使用指南

### **给团队成员的快速上手文档**

```markdown
# API使用指南

## 服务地址
- 生产环境: https://api.yourdomain.com
- 测试环境: http://test-api.yourdomain.com
- API文档: https://api.yourdomain.com/docs

## 认证
所有请求需要在Header中包含API Key:
X-API-Key: your-team-api-key

## Python示例
pip install requests
python client_sdk.py

## JavaScript示例
npm install axios form-data
node client_sdk.js

## 技术支持
- 文档: https://docs.yourdomain.com
- 问题反馈: support@yourdomain.com
```

---

完成！这份部署指南涵盖了从API集成到云端部署的完整流程。
