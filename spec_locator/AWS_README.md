# AWS EC2 + Docker 项目快速部署与调试指南

本指南总结在 AWS EC2 上部署、运行、调试 Docker 化后端服务（以 Spec Locator 为例）的常用流程与命令，适用于日常开发与运维。

---

## 一、基础环境检查

### 1. 登录服务器

```bash
ssh -i your_key.pem ec2-user@<EC2公网IP>
```

### 2. 查看系统信息

```bash
uname -a
free -h
df -h
```

### 3. 检查 Docker

```bash
docker --version
docker compose version
docker info
```

如未安装：

```bash
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

重新登录生效。

---

## 二、项目目录规范（推荐）

```text
/home/ec2-user/project/
├── output_pages/        # 业务数据（PDF 拆页结果）
├── uploads/             # 上传文件
├── logs/                # 日志
├── temp/                # 临时文件
├── Dockerfile
└── docker-compose.yml
```

原则：

* 项目私有数据放在 `~/project/`
* 不直接使用 `/data`（除非多项目共享）

---

## 三、构建镜像

进入含 Dockerfile 的目录：

```bash
cd ~/project
```

构建镜像：

```bash
docker build -t spec-locator:cpu .
```

查看镜像：

```bash
docker images
```

---

## 四、启动容器（推荐标准方式）

### 1. 停止并清理旧容器

```bash
docker rm -f spec-locator
```

### 2. 标准启动命令（带数据路径）

```bash
docker run -d \
  --name spec-locator \
  -p 8002:8002 \
  -v /home/ec2-user/project/output_pages:/app/data/output_pages:ro \
  -v /home/ec2-user/project/logs:/app/logs:rw \
  -v /home/ec2-user/project/temp:/app/temp:rw \
  -e SPEC_DATA_DIR=/app/data/output_pages \
  spec-locator:cpu
```

关键参数：

| 参数 | 含义        |
| -- | --------- |
| -p | 端口映射      |
| -v | Volume 挂载 |
| -e | 环境变量      |

---

## 五、容器状态管理

### 1. 查看运行状态

```bash
docker ps
```

### 2. 查看日志

```bash
docker logs spec-locator

docker logs -f spec-locator
```

### 3. 进入容器调试

```bash
docker exec -it spec-locator bash
```

---

## 六、数据与路径验证（必做）

### 1. 检查 Volume 是否正确

```bash
docker exec spec-locator ls /app/data/output_pages
```

### 2. 检查环境变量

```bash
docker exec spec-locator env | grep SPEC
```

应看到：

```text
SPEC_DATA_DIR=/app/data/output_pages
```

---

## 七、服务健康与接口测试

### 1. 本机测试

```bash
curl http://127.0.0.1:8002/health
```

### 2. 公网测试

```bash
curl http://<EC2公网IP>:8002/health
```

### 3. Swagger 文档

浏览器访问：

```text
http://<EC2公网IP>:8002/docs
```

---

## 八、网络与端口排查

### 1. 检查监听地址

```bash
ss -lntp | grep 8002
```

正确结果：

```text
0.0.0.0:8002
```

### 2. AWS 安全组

确保 Inbound Rule 放行：

```text
TCP 8002  0.0.0.0/0
```

---

## 九、索引 / 文件缺失排查

### 1. 查看真实文件名

```bash
docker exec spec-locator ls /app/data/output_pages/12J2
```

### 2. 确认接口参数匹配文件名

示例：

```text
C11-1.pdf  -> /api/download/12J2/C11-1
```

### 3. 常见错误

| 现象             | 原因        |
| -------------- | --------- |
| FILE_NOT_FOUND | 路径或文件名不匹配 |
| index=0        | 未初始化索引    |

---

## 十、Docker Compose（可选）

### 启动

```bash
docker compose up -d --build
```

### 停止

```bash
docker compose down
```

### 日志

```bash
docker compose logs -f
```

---

## 十一、资源监控

### 1. Docker 资源

```bash
docker stats
```

### 2. 系统资源

```bash
top
htop
free -h
```

---

## 十二、常用清理命令

### 删除无用容器

```bash
docker container prune
```

### 删除无用镜像

```bash
docker image prune -a
```

### 全量清理（慎用）

```bash
docker system prune -af
```

---

## 十三、推荐调试顺序（Checklist）

1. docker ps 是否运行
2. docker logs 是否报错
3. ss 是否 0.0.0.0
4. 安全组是否放行
5. Volume 是否正确
6. env 是否正确
7. /health 是否 OK
8. /docs 是否可访问
9. 数据路径是否匹配

---

## 十四、最佳实践

* 始终显式设置 DATA_DIR / SPEC_DATA_DIR
* 所有数据目录统一挂载
* 不依赖默认路径
* 生产环境使用 docker-compose
* 定期备份 data / logs
* 启动参数写入脚本

---

## 十五、快速启动模板（推荐收藏）

```bash
# 构建
docker build -t spec-locator:cpu .

# 清理旧容器
docker rm -f spec-locator

# 启动
docker run -d \
  --name spec-locator \
  -p 8002:8002 \
  -v ~/project/output_pages:/app/data/output_pages:ro \
  -e SPEC_DATA_DIR=/app/data/output_pages \
  spec-locator:cpu

# 验证
curl http://127.0.0.1:8002/health
```
