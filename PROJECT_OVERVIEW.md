# 建筑规范智能识别与检索系统

## 项目概述

本项目是一个基于AI技术的建筑规范智能识别与检索系统，主要用于从CAD截图中自动识别建筑规范编号和页码，并提供对应PDF文件的快速定位与下载。系统包含**核心规范定位服务**和**RAG智能问答扩展**两大功能模块。

---

## 🎯 核心功能：规范定位服务 (Spec Locator)

### 系统架构

规范定位服务采用模块化设计，包含以下核心组件：

```
图像输入 → 预处理 → 识别引擎 → 解析匹配 → 文件索引 → 结果输出
```

### 1. 双引擎识别系统

#### **OCR识别引擎（核心方式）**
- **技术栈**: PaddleOCR
- **特点**: 快速高效，启动时间<1秒
- **性能**: 识别速度<1秒
- **适用场景**: 清晰标准的CAD截图
- **核心流程**:
  - 图像预处理（去线、增强、二值化）
  - OCR文字识别（bbox坐标+文本）
  - 规范编号解析（支持12J2、L13J5-1等格式）
  - 页码识别（支持C11、1-11、123等多种格式）
  - 几何关系分析（邻近匹配、位置关联）
  - 置信度评估与排序

#### **LLM识别引擎（扩展方式）**
- **技术栈**: 支持多种大模型（豆包/ChatGPT/Gemini）
- **特点**: 智能理解，容错性强
- **性能**: 识别速度3-5秒
- **适用场景**: 模糊、倾斜、手写或复杂场景
- **优势**: 直接理解图像语义，无需复杂规则

### 2. 智能切换机制 (Auto模式)

系统提供三种识别模式：

| 模式 | 说明 | 速度 | 准确率 | 成本 |
|------|------|------|--------|------|
| **ocr** | 纯OCR识别 | ⚡ 快 (<1秒) | 中等 | 免费 |
| **llm** | 纯大模型识别 | 🐢 慢 (3-5秒) | 高 | 付费 |
| **auto** | 智能切换 | ⚖️ 适中 | 高 | 按需 |

**Auto模式策略**:
1. 优先使用OCR识别（快速+免费）
2. 判断OCR结果置信度
3. 低置信度时自动切换到LLM（准确+容错）
4. 返回最优结果

### 3. 文件索引与匹配

- **索引规模**: 2680+ PDF文件，涵盖所有常用建筑规范
- **智能匹配**: 
  - 规范编号模糊匹配（12J2 ↔ 12J2-1）
  - 页码范围识别（1-11、C11、123等）
  - 多候选结果排序
- **即时下载**: 识别成功后直接提供PDF文件下载

### 4. HTTP API服务

基于FastAPI构建的RESTful API：

**核心端点**:
- `POST /api/spec-locate` - 规范识别（支持method参数选择识别方式）
- `GET /api/download/{spec_code}/{page_code}` - 文件下载
- `GET /health` - 健康检查与系统状态

**响应示例**:
```json
{
  "success": true,
  "spec": {
    "code": "23J909",
    "page": "1-11",
    "confidence": 0.88
  },
  "file": {
    "path": "D:\\...\\output_pages\\23J909 工程做法\\23J909_1-11.pdf",
    "name": "23J909_1-11.pdf"
  },
  "candidates": [...]
}
```

### 5. 性能优化

- **懒加载**: OCR模型按需加载，避免启动延迟
- **后台预热**: 可选的后台模型预加载
- **并发支持**: 支持多用户同时访问
- **错误处理**: 完善的异常捕获与错误码系统

---

## 🚀 扩展功能：RAG智能问答系统

### 系统特点

基于检索增强生成（RAG）技术的建筑知识问答系统，提供两大知识库：

1. **建筑案例库** (anliku)
   - 实际工程案例
   - 施工方案示例
   - 最佳实践参考

2. **建筑规范库** (guifan)
   - 国家标准规范
   - 地方标准图集
   - 技术规程要求

### 核心技术

- **向量检索**: ChromaDB向量数据库
- **文档处理**: PDF解析、智能分块
- **多执行器架构**: 
  - `anliku_executor.py` - 案例库查询
  - `guifan_executor.py` - 规范库查询
  - `main_executor.py` - 统一调度
- **增量更新**: 基于哈希的文档去重与增量索引

### 功能特性

✅ 自然语言问答  
✅ 上下文检索  
✅ 多文档关联  
✅ 来源追溯

---

## 📦 系统部署

### 本地部署

```bash
# 启动规范定位服务
cd d:\projects\liuzong\spec_locator
start_demo.bat

# 访问服务
http://127.0.0.1:8002/         # Web界面
http://127.0.0.1:8002/docs     # API文档
```

### 云端部署

支持AWS EC2部署，使用Docker容器化：

```bash
# 访问地址
http://<EC2公网IP>:8002/
http://<EC2公网IP>:8002/docs
```

详见：[deploy_to_aws.md](deploy_to_aws.md)

---

## 🛠️ 技术栈

### 规范定位服务
- **框架**: FastAPI + Uvicorn
- **OCR引擎**: PaddleOCR
- **LLM引擎**: 豆包/ChatGPT/Gemini (可选)
- **图像处理**: OpenCV, NumPy
- **数据处理**: Python dataclasses

### RAG问答系统
- **向量数据库**: ChromaDB
- **文档处理**: PyPDF, LangChain
- **LLM**: 火山引擎大模型
- **嵌入模型**: 自定义Embedding

---

## 📊 项目规模

- **代码行数**: 2500+ 行核心代码
- **模块数量**: 8个核心模块
- **测试覆盖**: 单元测试 + 集成测试
- **文档数量**: 15+ 份技术文档
- **PDF索引**: 2680+ 份规范文件

---

## 🎯 使用场景

1. **建筑设计**：快速定位CAD图中引用的规范详图
2. **施工管理**：查找对应的施工标准与做法
3. **技术审查**：核对设计图纸中的规范引用
4. **知识检索**：智能问答获取规范和案例信息

---

## 📝 配置说明

### 环境变量配置

创建 `.env` 文件：

```bash
# 规范定位服务
SPEC_DATA_DIR=../output_pages
API_PORT=8002
LOG_LEVEL=INFO

# OCR配置
OCR_LAZY_LOAD=true
OCR_WARMUP_ON_STARTUP=true

# LLM配置（可选）
LLM_ENABLED=true
DOUBAO_API_KEY=your_api_key
LLM_PROVIDER=doubao
LLM_MODEL=doubao-pro-32k

# RAG配置（可选）
ARK_API_KEY=your_api_key
SEED_API_BASE=your_api_base_url
```

---

## 🚦 快速开始

### 1. 环境准备

```bash
# 使用uv (推荐)
uv venv
.\.venv\Scripts\Activate.ps1

# 或使用pip
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```bash
# 规范定位服务
pip install -r spec_locator/requirements.txt

# RAG系统（可选）
cd rag_demo
uv sync
```

### 3. 启动服务

```bash
# 方式1: 启动脚本
spec_locator\start_demo.bat

# 方式2: 手动启动
uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002
```

### 4. 测试功能

**Web界面测试**:
- 访问 http://127.0.0.1:8002/
- 上传CAD截图
- 选择识别方式（OCR/LLM/Auto）
- 查看识别结果并下载PDF

**API测试**:
```python
import requests

# OCR识别
response = requests.post(
    "http://127.0.0.1:8002/api/spec-locate",
    files={"file": open("cad_screenshot.png", "rb")},
    params={"method": "ocr"}
)

# 智能切换
response = requests.post(
    "http://127.0.0.1:8002/api/spec-locate",
    files={"file": open("cad_screenshot.png", "rb")},
    params={"method": "auto"}
)

print(response.json())
```

---

## 📚 文档索引

- [快速启动指南](spec_locator/readme.md)
- [LLM识别功能](spec_locator/LLM_README.md)
- [API文档](spec_locator/LLM_API_DOCS.md)
- [RAG系统指南](rag_demo/README.md)
- [AWS部署指南](deploy_to_aws.md)
- [Docker部署](DOCKER_README.md)
- [开发文档](spec_locator/README_DEV.md)
- [项目完成报告](spec_locator/PROJECT_SUMMARY.md)

---

## 💡 项目亮点

1. **双引擎架构**: OCR+LLM双保险，性能与准确率兼顾
2. **智能切换**: 自动选择最优识别方式，平衡速度与成本
3. **大规模索引**: 2680+规范文件智能匹配
4. **模块化设计**: 清晰的代码结构，易于扩展维护
5. **生产就绪**: 完善的错误处理、日志、监控和部署方案
6. **知识扩展**: RAG系统提供智能问答能力

---

## 📈 后续规划

- [ ] 支持批量图片识别
- [ ] 优化LLM识别速度（流式响应）
- [ ] 增加更多规范文件索引
- [ ] RAG系统与规范定位服务深度整合
- [ ] 移动端适配
- [ ] 用户反馈学习机制

---

*最后更新: 2026年1月*
