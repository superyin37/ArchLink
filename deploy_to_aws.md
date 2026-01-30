# AWS 部署指南 - Spec Locator Service

## 📋 版本更新说明

**v1.1.0 新增功能：**
- ✅ LLM视觉模型集成（支持豆包/OpenAI/Gemini）
- ✅ OCR + LLM 混合识别模式
- ✅ 自动降级机制（LLM失败时回退到OCR）
- ✅ 多提供商支持和配置灵活性

---

## 🚀 重新部署步骤

### 方式一：EC2 手动部署（推荐初次部署）

#### 1. 本地构建和测试
```powershell
# 确保环境变量配置正确
cp .env.example .env
# 编辑 .env 文件，填入你的 LLM API 密钥

# 构建新镜像
docker-compose build

# 本地测试
docker-compose up
```

#### 2. 推送镜像到 Amazon ECR

```powershell
# 配置 AWS CLI（如未配置）
aws configure

# 登录到 ECR
$AWS_ACCOUNT_ID = "<你的AWS账户ID>"
$AWS_REGION = "ap-northeast-1"  # 或你的区域
$REPO_NAME = "spec-locator"

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# 创建 ECR 仓库（首次部署）
aws ecr create-repository --repository-name $REPO_NAME --region $AWS_REGION

# 标记镜像
docker tag spec-locator:1.1.0 "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:1.1.0"
docker tag spec-locator:1.1.0 "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest"

# 推送镜像
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:1.1.0"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME:latest"
```

#### 3. 部署到 EC2

**A. SSH 连接到 EC2**
```powershell
ssh -i "<你的密钥>.pem" ec2-user@<EC2公网IP>
```

**B. 在 EC2 上准备环境**
```bash
# 安装 Docker 和 Docker Compose（如未安装）
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 登出并重新登录以应用组权限
exit
```

**C. 部署应用**
```bash
# 重新连接
ssh -i "<你的密钥>.pem" ec2-user@<EC2公网IP>

# 创建项目目录
mkdir -p ~/spec-locator
cd ~/spec-locator

# 登录 ECR
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin <账户ID>.dkr.ecr.ap-northeast-1.amazonaws.com

# 创建 docker-compose.yml（从本地复制或手动创建）
# 上传 .env 文件（包含 API 密钥）
nano .env  # 粘贴配置

# 更新 docker-compose.yml 中的镜像地址
nano docker-compose.yml
# 修改 image: 为 ECR 地址
# image: <账户ID>.dkr.ecr.ap-northeast-1.amazonaws.com/spec-locator:1.1.0

# 创建必要目录
mkdir -p output_pages spec_locator/uploads spec_locator/logs spec_locator/temp

# 上传 output_pages 数据（使用 scp 或 S3）
# 从本地上传：
# scp -i <密钥>.pem -r d:/projects/liuzong/output_pages ec2-user@<IP>:~/spec-locator/

# 停止旧容器（如有）
docker-compose down

# 拉取新镜像
docker-compose pull

# 启动新容器
docker-compose up -d

# 查看日志
docker-compose logs -f
```

#### 4. 验证部署
```bash
# 检查容器状态
docker ps

# 测试健康检查
curl http://localhost:8002/health

# 测试API（从本地）
curl http://<EC2公网IP>:8002/health
```

---

### 方式二：ECS/Fargate 部署

#### 1. 创建任务定义 (task-definition.json)
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
      "image": "<账户ID>.dkr.ecr.<区域>.amazonaws.com/spec-locator:1.1.0",
      "portMappings": [
        {
          "containerPort": 8002,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "SPEC_DATA_DIR", "value": "/app/data/output_pages"},
        {"name": "API_PORT", "value": "8002"},
        {"name": "LLM_ENABLED", "value": "true"},
        {"name": "LLM_PROVIDER", "value": "doubao"}
      ],
      "secrets": [
        {
          "name": "DOUBAO_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:<区域>:<账户ID>:secret:spec-locator/doubao-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/spec-locator",
          "awslogs-region": "<区域>",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### 2. 在 AWS Secrets Manager 中存储 API 密钥
```bash
aws secretsmanager create-secret \
  --name spec-locator/doubao-api-key \
  --secret-string "your-actual-api-key" \
  --region ap-northeast-1
```

#### 3. 注册任务定义并更新服务
```bash
# 注册任务定义
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 更新服务
aws ecs update-service \
  --cluster <集群名> \
  --service spec-locator-service \
  --task-definition spec-locator \
  --force-new-deployment
```

---

### 方式三：自动化部署脚本

创建 `deploy.ps1` 脚本：

```powershell
# 配置变量
$AWS_ACCOUNT_ID = "your-account-id"
$AWS_REGION = "ap-northeast-1"
$REPO_NAME = "spec-locator"
$EC2_IP = "your-ec2-ip"
$PEM_KEY = "path/to/your-key.pem"
$VERSION = "1.1.0"

# 构建镜像
Write-Host "Building Docker image..." -ForegroundColor Green
docker-compose build

# 登录 ECR
Write-Host "Logging in to ECR..." -ForegroundColor Green
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# 标记并推送镜像
Write-Host "Tagging and pushing image..." -ForegroundColor Green
$IMAGE_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME"
docker tag spec-locator:$VERSION "$IMAGE_URI:$VERSION"
docker tag spec-locator:$VERSION "$IMAGE_URI:latest"
docker push "$IMAGE_URI:$VERSION"
docker push "$IMAGE_URI:latest"

# 部署到 EC2
Write-Host "Deploying to EC2..." -ForegroundColor Green
ssh -i $PEM_KEY ec2-user@$EC2_IP @"
cd ~/spec-locator
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $IMAGE_URI
docker-compose pull
docker-compose down
docker-compose up -d
docker-compose logs --tail=50
"@

Write-Host "Deployment completed!" -ForegroundColor Green
Write-Host "Check health: http://$EC2_IP:8002/health" -ForegroundColor Yellow
```

---

## 🔐 安全配置

### 1. 使用 AWS Secrets Manager 管理 API 密钥

不要在 docker-compose.yml 中硬编码 API 密钥，使用环境变量或 Secrets Manager：

```yaml
environment:
  - LLM_ENABLED=true
  - LLM_PROVIDER=doubao
  # API密钥从 .env 文件或 AWS Secrets 读取
```

### 2. EC2 安全组配置

只开放必要端口：
- **入站规则**: 8002 端口（仅允许特定IP或负载均衡器）
- **出站规则**: 允许 HTTPS（443）用于访问 LLM API

### 3. 使用 ALB/NLB 负载均衡器

生产环境建议使用 Application Load Balancer：
- 配置 HTTPS 证书
- 启用健康检查：`/health`
- 配置访问日志

---

## 📊 监控和日志

### CloudWatch 日志配置

在 ECS 任务定义中配置：
```json
"logConfiguration": {
  "logDriver": "awslogs",
  "options": {
    "awslogs-group": "/ecs/spec-locator",
    "awslogs-region": "ap-northeast-1",
    "awslogs-stream-prefix": "ecs"
  }
}
```

### 关键监控指标

- **CPU 使用率**: 建议 < 70%
- **内存使用率**: 建议 < 80%
- **API 响应时间**: LLM 模式 < 30s，OCR 模式 < 5s
- **错误率**: < 1%

---

## 🔄 回滚策略

### 快速回滚到旧版本

**EC2:**
```bash
cd ~/spec-locator
docker-compose down
docker pull <ECR地址>:1.0.0
# 修改 docker-compose.yml 中的版本号
docker-compose up -d
```

**ECS:**
```bash
# 回滚到上一个任务定义版本
aws ecs update-service \
  --cluster <集群名> \
  --service spec-locator-service \
  --task-definition spec-locator:1  # 旧版本号
```

---

## 📝 部署检查清单

- [ ] 本地构建成功
- [ ] 本地测试通过
- [ ] LLM API 密钥已配置
- [ ] 镜像已推送到 ECR
- [ ] EC2/ECS 环境变量已更新
- [ ] output_pages 数据已同步
- [ ] 健康检查通过
- [ ] API 测试成功
- [ ] 日志无错误
- [ ] 监控告警已配置
- [ ] 回滚计划已准备

---

## 🆘 常见问题

### 1. LLM API 调用失败
- 检查 API 密钥是否正确配置
- 验证网络连接（EC2 需要访问外部 API）
- 查看日志中的详细错误信息

### 2. 镜像拉取失败
- 确认 ECR 权限配置正确
- 检查 IAM 角色是否有 ECR 访问权限
- 重新登录 ECR

### 3. 容器启动失败
- 检查环境变量配置
- 查看容器日志：`docker logs spec-locator`
- 验证 output_pages 目录是否存在

---

## 📞 支持

如有问题，请查看：
- 项目文档: [readme.md](readme.md)
- Docker 文档: [DOCKER_README.md](DOCKER_README.md)
- API 文档: http://\<EC2-IP\>:8002/docs
