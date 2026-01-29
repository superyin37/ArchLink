# 多LLM提供商支持 - 使用指南

## 概述

系统现已支持三种主流视觉大模型：
- **豆包** (Doubao) - 字节跳动
- **ChatGPT** (OpenAI) - gpt-4o/gpt-4-vision-preview
- **Gemini** (Google) - gemini-1.5-pro/gemini-1.5-flash

## 快速开始

### 1. 选择提供商

在 `.env` 文件中配置：

```bash
# 选择提供商
LLM_PROVIDER=doubao    # 或 openai 或 gemini

# 配置对应的API密钥
DOUBAO_API_KEY=your_key_here
# 或
OPENAI_API_KEY=your_key_here
# 或
GEMINI_API_KEY=your_key_here
```

### 2. 使用Doubao（豆包）

```bash
# .env配置
LLM_PROVIDER=doubao
DOUBAO_API_KEY=your_doubao_api_key
LLM_MODEL=doubao-vision-pro    # 可选，使用默认值
```

**特点：**
- 国内访问速度快
- 支持中文优化
- API端点：`ark.cn-beijing.volces.com`

### 3. 使用ChatGPT（OpenAI）

```bash
# .env配置
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
LLM_MODEL=gpt-4o    # 可选: gpt-4o, gpt-4-vision-preview, gpt-4-turbo
```

**特点：**
- 识别精度高
- 推理能力强
- 需要科学上网
- API端点：`api.openai.com`

### 4. 使用Gemini（Google）

```bash
# .env配置
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key
LLM_MODEL=gemini-1.5-pro    # 可选: gemini-1.5-pro, gemini-1.5-flash
```

**特点：**
- 免费额度较大
- 速度较快（flash模型）
- 需要科学上网
- API端点：`generativelanguage.googleapis.com`

## 完整配置示例

### 方式1：环境变量

**Windows PowerShell:**
```powershell
$env:LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="sk-xxx"
$env:LLM_MODEL="gpt-4o"
```

**Linux/Mac:**
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-xxx
export LLM_MODEL=gpt-4o
```

### 方式2：.env文件

```bash
# ===== 大模型配置 =====
LLM_ENABLED=true
LLM_PROVIDER=openai

# API密钥（只配置使用的提供商即可）
OPENAI_API_KEY=sk-xxx

# 模型名称（可选）
LLM_MODEL=gpt-4o

# 性能配置
LLM_TIMEOUT=30
LLM_MAX_RETRIES=2

# 混合模式配置
LLM_AUTO_FALLBACK=true
OCR_CONFIDENCE_THRESHOLD=0.6
```

## 三种识别模式

### 1. OCR模式（默认）

```python
POST /api/spec-locate?method=ocr
```

- 使用PaddleOCR识别
- 速度快（1-2秒）
- 适合清晰图片

### 2. LLM模式

```python
POST /api/spec-locate?method=llm
```

- 使用配置的大模型识别
- 精度高，处理复杂情况
- 速度较慢（3-10秒）

### 3. Auto模式（智能）

```python
POST /api/spec-locate?method=auto
```

- 先尝试OCR
- 如果置信度 < 0.6，自动切换到LLM
- 平衡速度和精度

## API密钥获取

### Doubao（豆包）

1. 访问：https://console.volcengine.com/ark
2. 注册/登录字节跳动火山引擎
3. 创建推理接入点
4. 获取 API Key

### OpenAI（ChatGPT）

1. 访问：https://platform.openai.com
2. 注册/登录 OpenAI 账号
3. 进入 API Keys 页面
4. 创建新的 API Key（以 `sk-` 开头）

### Gemini（Google）

1. 访问：https://makersuite.google.com/app/apikey
2. 登录 Google 账号
3. 点击 "Get API Key"
4. 创建新的 API Key

## 模型选择建议

| 场景 | 推荐提供商 | 推荐模型 | 原因 |
|------|----------|---------|------|
| **国内生产环境** | Doubao | doubao-vision-pro | 速度快，无需VPN |
| **追求最高精度** | OpenAI | gpt-4o | 识别能力最强 |
| **大量测试开发** | Gemini | gemini-1.5-flash | 免费额度大，速度快 |
| **成本敏感** | Gemini | gemini-1.5-flash | 免费额度充足 |
| **复杂场景** | OpenAI | gpt-4o | 推理能力强 |

## 性能对比

| 提供商 | 平均响应时间 | 识别精度 | 成本 | 网络要求 |
|--------|-------------|---------|------|---------|
| Doubao | 3-5秒 | ★★★★☆ | 中等 | 国内直连 |
| OpenAI | 5-8秒 | ★★★★★ | 较高 | 需要VPN |
| Gemini | 3-6秒 | ★★★★☆ | 低（有免费额度） | 需要VPN |

## 故障排查

### 问题1：API密钥无效

**错误信息：**
```
ValueError: ChatGPTEngine API key is required
```

**解决方法：**
1. 检查 `.env` 文件中的 API 密钥配置
2. 确认环境变量已正确设置
3. 验证密钥格式正确（OpenAI以`sk-`开头）

### 问题2：网络连接失败

**错误信息：**
```
requests.exceptions.ConnectionError
```

**解决方法：**
- Doubao: 检查国内网络连接
- OpenAI/Gemini: 检查VPN连接

### 问题3：提供商选择错误

**错误信息：**
```
Unknown LLM_PROVIDER: xxx
```

**解决方法：**
```bash
# 只能使用这三个值
LLM_PROVIDER=doubao    # ✓
LLM_PROVIDER=openai    # ✓
LLM_PROVIDER=gemini    # ✓
LLM_PROVIDER=gpt       # ✗ 错误
```

## 切换提供商

无需重启服务，只需修改环境变量即可：

```bash
# 停止服务
Ctrl+C

# 修改配置
$env:LLM_PROVIDER="gemini"
$env:GEMINI_API_KEY="your_key"

# 重新启动
uvicorn spec_locator.api.server:app --port 8002
```

## 测试验证

```bash
# 运行集成测试
python test_llm_integration.py

# 测试特定提供商
$env:LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="sk-xxx"
python test_llm_integration.py
```

## 常见问题

**Q: 可以同时配置多个提供商吗？**  
A: 可以在 `.env` 中配置多个 API 密钥，通过 `LLM_PROVIDER` 切换使用哪个。

**Q: 哪个提供商最便宜？**  
A: Gemini 有慷慨的免费额度，适合开发测试。生产环境建议根据实际调用量评估。

**Q: 识别效果差异大吗？**  
A: 三个模型在清晰图片上效果相近，复杂场景下 GPT-4o 表现最好。

**Q: 如何提高识别速度？**  
A: 使用 Auto 模式，让清晰图片走 OCR（1-2秒），复杂图片才用 LLM。

## 进阶配置

### 自定义超时时间

```bash
LLM_TIMEOUT=60    # 适合网络较慢的情况
```

### 调整重试次数

```bash
LLM_MAX_RETRIES=5    # 增加重试次数提高成功率
```

### 修改置信度阈值

```bash
OCR_CONFIDENCE_THRESHOLD=0.7    # 提高阈值，更多使用LLM
```

## 技术架构

```
BaseLLMEngine (抽象基类)
    ├── DoubaoEngine   - 豆包实现
    ├── ChatGPTEngine  - OpenAI实现
    └── GeminiEngine   - Google实现

PromptManager
    └── build_messages(provider)  # 根据提供商生成不同格式

Pipeline
    └── 根据 LLMConfig.PROVIDER 动态加载引擎
```

## 代码示例

```python
from spec_locator.llm import ChatGPTEngine, GeminiEngine, DoubaoEngine
import cv2

# 读取图片
image = cv2.imread("test.jpg")

# 使用ChatGPT
chatgpt = ChatGPTEngine(api_key="sk-xxx", model="gpt-4o")
result = chatgpt.recognize(image)
print(result)  # {"success": True, "spec_code": "12J2", "page_code": "C11"}

# 使用Gemini
gemini = GeminiEngine(api_key="your_key", model="gemini-1.5-pro")
result = gemini.recognize(image)

# 使用豆包
doubao = DoubaoEngine(api_key="your_key")
result = doubao.recognize(image)
```

## 总结

现在系统支持灵活切换三种主流视觉大模型，可以根据实际需求（成本、速度、精度、网络环境）选择最合适的方案。推荐：
- **开发测试**: Gemini（免费额度大）
- **国内生产**: Doubao（无需VPN）
- **追求极致**: OpenAI GPT-4o（识别最准）
