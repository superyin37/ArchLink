# 🚀 安装指南汇总

快速安装 Spec Locator Service 的多种方式。

---

## ⚡ 最快方式（推荐）

### 如果已安装 uv

```bash
cd spec_locator
uv sync --dev
source venv/bin/activate
python main.py
```

**时间**: ~5 秒

---

## 🖱️ 一键启动（平台相关）

### Windows (PowerShell)
```powershell
cd spec_locator
python setup.py
```

或直接运行：
```powershell
.\setup.bat
```

### Linux / macOS
```bash
cd spec_locator
chmod +x setup.sh
./setup.sh
```

或用 Python：
```bash
cd spec_locator
python setup.py
```

---

## 📋 标准安装步骤

### 1️⃣ 安装 uv（可选但强烈推荐）

#### Windows
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Linux/macOS
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 或使用 pip
```bash
pip install uv
```

### 2️⃣ 创建虚拟环境

#### 使用 uv（推荐）
```bash
cd spec_locator
uv venv venv
```

#### 使用 pip
```bash
cd spec_locator
python -m venv venv
```

### 3️⃣ 激活虚拟环境

#### Windows (PowerShell)
```powershell
.\venv\Scripts\Activate.ps1
```

#### Windows (cmd)
```cmd
venv\Scripts\activate
```

#### Linux/macOS
```bash
source venv/bin/activate
```

### 4️⃣ 安装依赖

#### 使用 uv（推荐，最快）
```bash
uv pip install -e ".[dev]"
```

#### 使用 pip
```bash
pip install -e ".[dev]"
```

### 5️⃣ 启动服务

```bash
python main.py
```

---

## 🎯 速度对比

| 方式 | 首次安装 | 二次启动 | 备注 |
|------|---------|---------|------|
| uv | ~3 秒 | <1 秒 | ⚡ 最快 |
| pip | ~30 秒 | ~5 秒 | 传统方式 |
| setup.bat/.sh | ~10 秒 | <1 秒 | 一键启动 |
| setup.py | ~15 秒 | <1 秒 | 跨平台 |

---

## ✅ 验证安装

### 健康检查
```bash
curl http://localhost:8000/health
```

预期响应：
```json
{"status": "ok"}
```

### 测试识别
```bash
curl -X POST http://localhost:8000/api/spec-locate \
  -F "file=@sample.png"
```

---

## 🔧 故障排查

### 问题：ImportError: No module named 'paddleocr'

**解决**：
```bash
# 确保在虚拟环境中
python -m pip install paddleocr
```

### 问题：port 8000 already in use

**解决**：
```bash
# 使用其他端口
export API_PORT=8001
python main.py

# 或杀死现有进程
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows
```

### 问题：uv command not found

**解决**：
```bash
# 重新安装 uv
pip install uv

# 或使用官方安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 📚 更多帮助

- 📖 [UV_GUIDE.md](UV_GUIDE.md) - uv 详细使用指南
- 📖 [DEVELOPMENT.md](DEVELOPMENT.md) - 开发指南
- 📖 [README_DEV.md](README_DEV.md) - 完整文档
- 📖 [QUICK_REFERENCE.py](QUICK_REFERENCE.py) - 快速参考

---

## 🎬 常见工作流

### 日常开发
```bash
# 第一次
uv sync --dev
source venv/bin/activate

# 后续每次
source venv/bin/activate
python main.py
```

### 更新依赖
```bash
uv pip install --upgrade -e ".[dev]"
```

### 生成锁文件（用于 CI/Docker）
```bash
uv pip compile pyproject.toml --extra dev -o requirements.txt
```

### 离线安装
```bash
# 生成 wheels
uv pip download -e ".[dev]" -d wheels/

# 离线安装
uv pip install --no-index --find-links wheels/ -e ".[dev]"
```

---

**选择最适合你的方式开始吧！** 🎉
