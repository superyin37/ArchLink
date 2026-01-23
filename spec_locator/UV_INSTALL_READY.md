# ✨ uv 环境支持已添加

你现在可以使用 **uv** 快速安装开发环境！

## 🚀 最快开始（3 秒）

```bash
# 安装 uv（如果没有）
pip install uv

# 进入项目目录
cd spec_locator

# 一键安装
uv sync --dev

# 激活环境
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# 启动服务
python main.py
```

## 📦 支持的 3 种安装方式

### 方式 1️⃣：uv（最快，推荐）
```bash
uv sync --dev
```
⚡ 速度：~3 秒 | 🎯 推荐用于：快速开发、CI/CD

### 方式 2️⃣：自动脚本（智能选择）
```bash
python setup.py
```
⏱️ 速度：~10-15 秒 | 🎯 推荐用于：新手、跨平台

### 方式 3️⃣：传统 pip（可靠）
```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```
⏱️ 速度：~30 秒 | 🎯 推荐用于：稳定性优先

## 🖱️ 一键启动脚本

### Windows
直接运行 `setup.bat`，会自动：
1. 检查 Python
2. 创建虚拟环境（如果需要）
3. 安装依赖
4. 启动服务

### Linux/macOS
```bash
chmod +x setup.sh
./setup.sh
```

## 📚 详细文档

| 文档 | 内容 | 适合人群 |
|------|------|--------|
| [INSTALL.md](INSTALL.md) | 各种安装方式详解 | 所有人 |
| [UV_GUIDE.md](UV_GUIDE.md) | uv 完整使用手册 | 想深入了解 uv |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 开发指南 | 开发者 |
| [README_DEV.md](README_DEV.md) | 完整项目文档 | 所有人 |

## ⚙️ 新增文件

```
✓ setup.py          自动安装脚本（跨平台）
✓ setup.bat         Windows 一键启动
✓ setup.sh          Linux/macOS 一键启动
✓ INSTALL.md        安装指南汇总
✓ UV_GUIDE.md       uv 详细使用指南
```

## 💡 快速命令参考

```bash
# 使用 uv 快速管理
uv sync --dev              # 一键安装所有依赖
uv pip install <package>   # 安装单个包
uv pip list                # 列出已安装包
uv pip compile -o requirements.txt  # 生成锁文件

# 日常开发
source venv/bin/activate   # 激活虚拟环境
python main.py             # 启动服务
pytest tests/              # 运行测试
```

## 🎯 选择哪种方式？

### 如果你想要...

| 需求 | 选择 |
|------|------|
| 最快速度 | `uv sync --dev` |
| 最简单（Windows） | `setup.bat` |
| 最简单（Linux/macOS） | `./setup.sh` |
| 完全自动 | `python setup.py` |
| 传统稳定 | `pip install -e ".[dev]"` |

## ✅ 验证安装

```bash
# 检查 Python
python --version

# 检查虚拟环境
which python  # 应该显示 venv 路径

# 检查 API
curl http://localhost:8000/health
```

## 🆘 常见问题

**Q: 为什么用 uv？**  
A: uv 比 pip 快 10-100 倍，特别是在重新安装或解决依赖冲突时。

**Q: uv 和 pip 能混用吗？**  
A: 不推荐，但技术上可行。建议选择一个坚持使用。

**Q: 已经用 pip 安装了，能切换到 uv 吗？**  
A: 完全可以。删除 venv，用 uv 重新创建即可。

**Q: 是否需要装 uv？**  
A: 不是必需的，但强烈推荐。setup.py 会自动安装。

---

**现在开始吧！** 🎉

选择上面任意一种方式安装环境，然后 `python main.py` 启动服务！
