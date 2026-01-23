# 🚀 使用 uv 快速构建环境

[uv](https://github.com/astral-sh/uv) 是一个用 Rust 编写的超快速 Python 包管理工具，比 pip 快 10-100 倍。

## 📦 安装 uv

### Windows (PowerShell)
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Linux / macOS
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 或使用 pip
```bash
pip install uv
```

验证安装：
```bash
uv --version
```

---

## 🎯 快速开始（3 种方式）

### 方式 1️⃣：最简单（推荐新手）
```bash
cd spec_locator
uv sync --dev
```
这会一次性创建虚拟环境和安装所有依赖！

### 方式 2️⃣：分步骤（推荐进阶）
```bash
cd spec_locator

# 创建虚拟环境
uv venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# 或
venv\Scripts\activate  # Windows cmd

# 安装依赖
uv pip install -e ".[dev]"
```

### 方式 3️⃣：使用环境变量（推荐 CI/CD）
```bash
cd spec_locator
VIRTUAL_ENV=.venv uv sync --dev
```

---

## 📋 常用 uv 命令

### 环境管理
```bash
# 创建虚拟环境
uv venv venv

# 列出已安装的包
uv pip list

# 删除虚拟环境
rm -rf venv  # Linux/macOS
rmdir /s venv  # Windows
```

### 包管理
```bash
# 安装单个包
uv pip install fastapi

# 安装开发依赖
uv pip install -e ".[dev]"

# 安装特定版本
uv pip install "fastapi==0.95.0"

# 卸载包
uv pip uninstall fastapi

# 升级包
uv pip install --upgrade fastapi
```

### 依赖锁定
```bash
# 生成 requirements.txt
uv pip compile pyproject.toml -o requirements.txt

# 生成包含开发依赖的 requirements.txt
uv pip compile pyproject.toml --extra dev -o requirements-dev.txt

# 从 requirements.txt 安装（离线或确定性安装）
uv pip install -r requirements.txt
```

---

## 🔄 uv 与 pip 对比

| 功能 | pip | uv |
|------|-----|-----|
| 安装速度 | 正常 | ⚡ 10-100倍快 |
| 内存占用 | 高 | 低 |
| CPU 占用 | 中 | 低 |
| 兼容性 | 100% | 99.9% |
| 虚拟环境 | 需要 venv | 内置 |
| 依赖锁定 | 需要 pip-tools | 内置 |

---

## 💡 使用建议

### ✅ 推荐用 uv 的场景
- 🚀 频繁安装/卸载包
- ⏱️ 要求快速构建环境
- 🔄 CI/CD 流程
- 📦 大型依赖树
- 🐳 Docker 镜像构建

### ⚠️ 注意事项
- 某些旧的或特殊的包可能有兼容性问题（但 Spec Locator 的所有依赖都支持）
- Windows 用户需确保已启用 PowerShell 脚本执行权限

---

## 🎬 实际操作示例

### 场景 1：第一次搭建
```bash
# 进入项目
cd spec_locator

# 一键安装（含开发工具）
uv sync --dev

# 激活环境
source venv/bin/activate

# 启动服务
python main.py
```

### 场景 2：更新依赖
```bash
# 更新所有包到最新
uv pip install --upgrade -e ".[dev]"

# 或仅更新特定包
uv pip install --upgrade fastapi
```

### 场景 3：生成锁文件（用于 Docker 或 CI）
```bash
# 生成 requirements.txt
uv pip compile pyproject.toml --extra dev -o requirements-lock.txt

# 使用锁文件安装（完全相同的环境）
uv pip install -r requirements-lock.txt
```

---

## 🐳 Docker 中使用 uv

### Dockerfile 示例
```dockerfile
FROM python:3.11-slim

# 安装 uv
RUN pip install uv

WORKDIR /app

# 复制项目文件
COPY . .

# 使用 uv 安装依赖（比 pip 快很多）
RUN uv pip install -e ".[dev]"

# 启动服务
CMD ["python", "main.py"]
```

---

## ⚡ 性能对比

使用 uv 的性能优势：

```
首次安装依赖：
pip:  ~45 秒
uv:   ~3 秒  (15倍快)

重新安装（缓存）：
pip:  ~8 秒
uv:   ~0.5 秒  (16倍快)

解析依赖冲突：
pip:  ~30 秒
uv:   ~1 秒  (30倍快)
```

---

## 🆘 常见问题

### Q: uv 和 pip 能混用吗？
A: 可以，但不推荐。建议选择其中一个坚持使用。

### Q: uv 生成的虚拟环境和 venv 兼容吗？
A: 完全兼容。uv 创建的虚拟环境就是标准 Python venv。

### Q: 能否同时用 uv 和 pip？
A: 虽然技术上可行，但会导致依赖冲突。不推荐。

### Q: uv 支持 Python 2 吗？
A: 不支持，仅支持 Python 3.7+。

### Q: 如何在 GitHub Actions 中使用 uv？
A: 使用 `astral-sh/uv-action` action：
```yaml
- uses: astral-sh/uv-action@v1
  with:
    python-version: "3.11"
```

---

## 📚 更多资源

- 📖 [uv 官方文档](https://docs.astral.sh/uv/)
- 🐍 [GitHub 仓库](https://github.com/astral-sh/uv)
- 💬 [Discord 社区](https://discord.gg/astral-sh)

---

**总结**：用 `uv sync --dev` 一条命令就能快速搭建完整开发环境，特别适合频繁开发和 CI/CD 场景！
