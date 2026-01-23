# Spec Locator Service - 文件导航指南

## 📖 项目文件导航

### 核心模块文件

| 文件路径 | 行数 | 说明 |
|---------|------|------|
| [api/server.py](api/server.py) | ~150 | HTTP API 接口（FastAPI） |
| [config/config.py](config/config.py) | ~150 | 全局配置管理 |
| [core/pipeline.py](core/pipeline.py) | ~140 | 核心流水线 |
| [ocr/ocr_engine.py](ocr/ocr_engine.py) | ~140 | OCR 引擎封装（PaddleOCR） |
| [parser/geometry.py](parser/geometry.py) | ~200 | 几何关系计算 |
| [parser/spec_code.py](parser/spec_code.py) | ~170 | 规范编号识别 |
| [parser/page_code.py](parser/page_code.py) | ~180 | 页码识别与组合 |
| [postprocess/confidence.py](postprocess/confidence.py) | ~150 | 置信度评估 |
| [preprocess/image_preprocess.py](preprocess/image_preprocess.py) | ~160 | 图像预处理 |

### 文档文件

| 文件路径 | 说明 | 适用人员 |
|---------|------|--------|
| [README_DEV.md](README_DEV.md) | 完整开发文档 | 开发者 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 快速开发指南 | 开发者 |
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | 项目完成总结 | 经理/架构师 |
| [examples.py](examples.py) | 使用示例代码 | 开发者 |

### 配置和入口文件

| 文件路径 | 说明 |
|---------|------|
| [main.py](main.py) | 程序入口，启动 HTTP 服务 |
| [pyproject.toml](pyproject.toml) | 项目依赖和元数据 |

### 测试文件

| 文件路径 | 说明 |
|---------|------|
| [tests/test_spec_code.py](tests/test_spec_code.py) | 规范编号识别测试 |
| [tests/test_geometry.py](tests/test_geometry.py) | 几何关系计算测试 |

### 初始化文件

所有 `__init__.py` 文件用于模块导出和初始化：
- [api/__init__.py](api/__init__.py)
- [config/__init__.py](config/__init__.py)
- [core/__init__.py](core/__init__.py)
- [ocr/__init__.py](ocr/__init__.py)
- [parser/__init__.py](parser/__init__.py)
- [postprocess/__init__.py](postprocess/__init__.py)
- [preprocess/__init__.py](preprocess/__init__.py)
- [tests/__init__.py](tests/__init__.py)

---

## 🗂️ 按功能查找

### 想要...

#### 启动服务？
👉 查看 [main.py](main.py) 或 [README_DEV.md#快速开始](README_DEV.md#快速开始)

#### 调用 API？
👉 查看 [api/server.py](api/server.py) 的 `/api/spec-locate` 端点

#### 修改配置？
👉 编辑 [config/config.py](config/config.py)

#### 改进规范编号识别？
👉 修改 [parser/spec_code.py](parser/spec_code.py)

#### 改进页码识别？
👉 修改 [parser/page_code.py](parser/page_code.py) 和 [parser/geometry.py](parser/geometry.py)

#### 调整置信度权重？
👉 编辑 [config/config.py](config/config.py) 中的 `ConfidenceConfig`

#### 学习使用方法？
👉 运行 [examples.py](examples.py) 查看示例

#### 添加新的测试？
👉 在 [tests/](tests/) 目录中创建 `test_*.py` 文件

#### 了解完整的架构？
👉 查看 [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

#### 快速开发参考？
👉 查看 [DEVELOPMENT.md](DEVELOPMENT.md)

---

## 📋 开发流程清单

### 1. 环境准备
- [ ] 克隆项目
- [ ] 创建虚拟环境: `python -m venv venv`
- [ ] 激活虚拟环境
- [ ] 安装依赖: `pip install -e ".[dev]"`

### 2. 启动开发
- [ ] 运行 `python main.py` 启动 API 服务
- [ ] 运行 `pytest tests/` 执行测试
- [ ] 运行 `python examples.py` 了解使用方法

### 3. 修改代码
- [ ] 修改相应模块文件
- [ ] 执行相关测试验证
- [ ] 查看日志输出

### 4. 测试 API
- [ ] `curl http://localhost:8000/health` 检查服务
- [ ] `curl -X POST http://localhost:8000/api/spec-locate -F "file=@sample.png"` 测试识别

### 5. 提交代码
- [ ] 确保所有测试通过
- [ ] 确保代码风格一致 (使用 black, isort)
- [ ] 更新相关文档

---

## 🔍 常见问题快速定位

### 问题：识别不准确
**相关文件**：
- 调整图像预处理: [preprocess/image_preprocess.py](preprocess/image_preprocess.py)
- 调整规范编号识别: [parser/spec_code.py](parser/spec_code.py)
- 调整页码识别: [parser/page_code.py](parser/page_code.py)
- 调整置信度: [postprocess/confidence.py](postprocess/confidence.py)

### 问题：启动失败
**相关文件**：
- 检查配置: [config/config.py](config/config.py)
- 查看日志: 配置日志路径在 [main.py](main.py)

### 问题：依赖缺失
**相关文件**：
- 查看依赖: [pyproject.toml](pyproject.toml)
- 重新安装: `pip install -e ".[dev]"`

### 问题：API 返回错误
**相关文件**：
- 查看错误码: [config/config.py](config/config.py) 中的 `ErrorCode`
- 查看 API 实现: [api/server.py](api/server.py)
- 查看流水线: [core/pipeline.py](core/pipeline.py)

---

## 🧠 模块依赖关系

```
api/server.py
    ├── config/config.py
    ├── core/pipeline.py
    │   ├── preprocess/image_preprocess.py
    │   ├── ocr/ocr_engine.py
    │   ├── parser/spec_code.py
    │   ├── parser/page_code.py
    │   │   └── parser/geometry.py
    │   └── postprocess/confidence.py
    └── 其他各模块
```

---

## 📚 文档阅读顺序

**新手开发者推荐**：
1. 本文件 (FILE_NAVIGATION.md) - 快速定位
2. [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 项目概览
3. [README_DEV.md](README_DEV.md) - 详细说明
4. [DEVELOPMENT.md](DEVELOPMENT.md) - 快速指南
5. [examples.py](examples.py) - 实际使用
6. 源代码注释 - 具体实现

**运维人员推荐**：
1. [README_DEV.md](README_DEV.md#部署指南) - 部署说明
2. [config/config.py](config/config.py) - 配置参数
3. [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md#性能指标) - 性能指标

**架构师推荐**：
1. [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 项目设计
2. [README_DEV.md](README_DEV.md#系统架构) - 架构详解
3. [core/pipeline.py](core/pipeline.py) - 核心流程

---

## 🎯 快速命令参考

```bash
# 启动服务
python main.py

# 启动 API（开发模式，支持热重载）
uvicorn api.server:app --reload

# 运行所有测试
pytest tests/ -v

# 运行指定测试
pytest tests/test_spec_code.py -v

# 查看代码覆盖率
pytest --cov=. --cov-report=html

# 格式化代码
black .
isort .

# 运行 linter
flake8 .

# 运行示例
python examples.py
```

---

## 📊 统计信息

- **总文件数**: 21 个
- **Python 文件**: 19 个
- **文档文件**: 4 个
- **总代码行数**: ~2,500+
- **模块数**: 8 个
- **数据类**: 10+ 个
- **类方法**: 50+ 个

---

## 🔗 重要链接

- **项目根目录**: `D:\projects\liuzong\spec_locator\`
- **主程序**: `main.py`
- **API 地址**: `http://localhost:8000`
- **API 文档**: `http://localhost:8000/docs` (启动后自动生成)

---

**最后更新**: 2026-01-15
**版本**: v1.0.0
