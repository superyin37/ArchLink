# 前端集成与API调用详解

本文档详细说明了演示页面的设计思路、与后端的关系，以及完整的API调用逻辑。

---

## 📋 目录

1. [系统架构与修改说明](#系统架构与修改说明)
2. [页面关系说明](#页面关系说明)
3. [API调用完整逻辑](#api调用完整逻辑)
4. [关键技术点](#关键技术点)

---

## 系统架构与修改说明

### 1. **后端增强** - 添加自动下载功能

#### 核心修改：[core/pipeline.py](core/pipeline.py#L126-L133)

在POST响应中添加了 `download_url` 字段，让前端知道如何下载PDF文件：

```python
def _success_response(self, matches: List[SpecMatch]) -> Dict[str, Any]:
    """生成成功响应"""
    best_match = matches[0]
    
    # 查找对应的PDF文件
    pdf_file = self.file_index.find_file(best_match.spec_code, best_match.page_code)
    
    response = {
        "success": True,
        "spec": {
            "code": best_match.spec_code,
            "page": best_match.page_code,
            "confidence": round(best_match.confidence, 4),
        },
        "candidates": [...],
    }
    
    # 如果找到PDF文件，添加文件信息和下载URL
    if pdf_file:
        download_url = f"/api/download/{best_match.spec_code}/{best_match.page_code}"
        response["file"] = {
            "path": pdf_file.file_path,
            "name": pdf_file.file_name,
            "directory": pdf_file.directory,
            "download_url": download_url,  # ← 新增字段
        }
    
    return response
```

**响应示例：**
```json
{
  "success": true,
  "spec": {
    "code": "12J2",
    "page": "C11",
    "confidence": 0.7834
  },
  "file": {
    "path": "D:\\projects\\liuzong\\output_pages\\12J2\\12J2_C11.pdf",
    "name": "12J2_C11.pdf",
    "directory": "12J2",
    "download_url": "/api/download/12J2/C11"  ← 前端使用此URL下载
  },
  "candidates": [...]
}
```

#### CORS支持：[api/server.py](api/server.py#L16-L32)

添加了跨域资源共享支持，允许前端页面访问API：

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(...)

# 添加 CORS 中间件，允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 2. **创建演示页面** - [api/demo.html](api/demo.html)

这是一个**完整的前端用户界面**，提供了友好的交互体验。

#### UI组件设计

| 组件 | 功能 | 实现方式 |
|------|------|----------|
| 📤 **上传区域** | 点击/拖拽上传图片 | HTML5 Drag & Drop API |
| 🖼️ **图片预览** | 实时显示上传的图片 | FileReader API |
| ⏳ **加载动画** | 识别过程中的视觉反馈 | CSS动画 + 条件显示 |
| 📊 **结果卡片** | 显示规范编号、页码、置信度 | 动态填充DOM |
| ⬇️ **下载按钮** | 一键下载PDF文件 | `<a>` 标签 + download属性 |
| 📋 **候选列表** | 显示其他可能的匹配 | 动态生成列表项 |
| ❌ **错误提示** | 友好的错误信息 | 条件显示 + 自定义样式 |

#### 交互流程图

```
┌──────────────┐
│ 用户上传图片  │
│ (点击/拖拽)  │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ 显示图片预览      │
│ 显示加载动画      │
└──────┬───────────┘
       │
       ▼
┌──────────────────────────┐
│ POST /api/spec-locate    │
│ 上传图片到后端            │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ 后端OCR识别 + 文件查找   │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ 返回识别结果              │
│ + download_url (如有文件) │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ 显示识别结果              │
│ 显示下载按钮(如有文件)    │
│ 显示候选结果              │
└──────┬───────────────────┘
       │
       │ (用户点击下载)
       ▼
┌──────────────────────────┐
│ GET /api/download/...    │
│ 浏览器自动下载PDF         │
└──────────────────────────┘
```

---

### 3. **修复兼容性问题**

#### OCR引擎修复：[ocr/ocr_engine.py](ocr/ocr_engine.py#L69-L80)

禁用OneDNN优化，解决PaddlePaddle PIR兼容性问题：

```python
self.recognizer = PaddleOCR(
    use_angle_cls=True,
    lang="ch",
    device='cpu',
    enable_mkldnn=False,  # ← 关键修复：禁用OneDNN
    use_mp=False,         # ← 禁用多进程
)
```

**问题原因：** PaddlePaddle 3.x的PIR（Program Intermediate Representation）与OneDNN/MKL-DNN优化不兼容

#### 版本控制

| 组件 | 之前版本 | 当前版本 | 原因 |
|------|---------|---------|------|
| **PaddlePaddle** | 3.3.0 | 2.6.2 | 避免PIR兼容性问题 |
| **PaddleOCR** | 3.3.2 | 2.8.1 | 与Paddle版本匹配 |
| **NumPy** | 2.2.6 | 1.26.4 | 兼容Paddle 2.x |

---

## 页面关系说明

### **127.0.0.1:8002/docs** (Swagger API文档)

**类型：** FastAPI自动生成的交互式API文档

**用途：** 
- 🔧 **开发者工具** - 用于调试和测试API
- 📖 **API参考** - 查看所有端点的详细说明
- 🧪 **在线测试** - 直接在浏览器中调用API

**功能：**
- 查看所有API端点（GET /health, POST /api/spec-locate, GET /api/download等）
- 查看请求/响应的数据结构
- 测试API请求并查看响应
- 自动生成curl命令示例

**访问方式：**
```bash
# 启动服务器后访问
http://127.0.0.1:8002/docs
```

---

### **api/demo.html** (用户演示界面)

**类型：** 自定义的HTML单页应用

**用途：**
- 👥 **终端用户界面** - 提供友好的图形界面
- 🎨 **可视化展示** - 美观的结果呈现
- 🚀 **一键操作** - 简化用户交互流程

**功能：**
- 拖拽/点击上传CAD截图
- 实时预览上传的图片
- 可视化显示识别结果
- 一键下载PDF文件
- 显示多个候选结果
- 友好的错误提示

**访问方式：**
```bash
# 直接在浏览器中打开本地文件
file:///D:/projects/liuzong/spec_locator/api/demo.html

# 或者通过HTTP服务器（如需要）
python -m http.server 8080
# 然后访问 http://localhost:8080/api/demo.html
```

---

### **两者关系对比**

```
┌───────────────────────────────────────────────────┐
│         FastAPI 后端服务器 (127.0.0.1:8002)        │
│                                                   │
│  ┌──────────────────┐    ┌──────────────────┐   │
│  │   API 端点        │    │   Swagger UI     │   │
│  │                  │    │   (/docs)        │   │
│  │  POST /api/*     │    │                  │   │
│  │  GET /health     │    │  自动生成的       │   │
│  │  GET /download/* │    │  API文档界面      │   │
│  └────────┬─────────┘    └────────┬─────────┘   │
└───────────┼──────────────────────┼───────────────┘
            │                      │
            │ AJAX请求              │ 浏览器访问
            │ (JSON)               │ (HTML)
            │                      │
     ┌──────┴──────┐        ┌─────┴──────┐
     │             │        │            │
     │  demo.html  │        │  开发者    │
     │  (用户界面) │        │  (调试)    │
     │             │        │            │
     └─────────────┘        └────────────┘
         │                       │
         ▼                       ▼
    终端用户使用              开发者测试
```

### **使用场景对比**

| 特性 | Swagger UI (/docs) | demo.html |
|------|-------------------|-----------|
| **目标用户** | 开发者、测试人员 | 终端用户 |
| **界面风格** | 技术文档风格 | 友好的用户界面 |
| **主要用途** | API调试、测试 | 实际业务使用 |
| **上传方式** | 表单选择文件 | 拖拽/点击上传 |
| **结果展示** | JSON原始数据 | 可视化卡片 |
| **下载方式** | 手动构造URL | 一键下载按钮 |
| **错误处理** | 显示HTTP状态码 | 友好的错误提示 |

---

## API调用完整逻辑

### 1. 配置与初始化

```javascript
// demo.html 开始部分
const API_BASE_URL = 'http://127.0.0.1:8002';  // API服务器地址

// 获取DOM元素
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const previewArea = document.getElementById('previewArea');
const previewImg = document.getElementById('previewImg');
const loading = document.getElementById('loading');
const resultArea = document.getElementById('resultArea');
const errorMessage = document.getElementById('errorMessage');
```

---

### 2. 文件上传触发机制

#### **方式A：点击上传**

```javascript
// 点击上传区域 → 触发隐藏的file input
uploadArea.addEventListener('click', () => fileInput.click());

// file input选择文件后
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);  // ← 调用主处理函数
    }
});
```

**HTML结构：**
```html
<div class="upload-area" id="uploadArea">
    <div class="upload-icon">📁</div>
    <div class="upload-text">点击或拖拽图片到此处上传</div>
    <input type="file" id="fileInput" accept="image/*" style="display: none;">
</div>
```

#### **方式B：拖拽上传**

```javascript
// 1. 拖拽进入 → 添加视觉效果
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();  // 阻止默认行为（打开文件）
    uploadArea.classList.add('dragover');  // 添加CSS样式
});

// 2. 拖拽离开 → 移除视觉效果
uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

// 3. 放下文件 → 获取文件并处理
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();  // 阻止浏览器打开文件
    uploadArea.classList.remove('dragover');
    
    const file = e.dataTransfer.files[0];  // 获取第一个文件
    if (file) {
        handleFile(file);  // ← 调用主处理函数
    }
});
```

---

### 3. 核心处理函数详解

#### **完整代码与注释**

```javascript
async function handleFile(file) {
    // ============================================
    // 步骤1: 显示图片预览
    // ============================================
    const reader = new FileReader();
    
    // 文件读取完成后的回调
    reader.onload = (e) => {
        previewImg.src = e.target.result;  // Base64图片数据
        previewArea.style.display = 'block';  // 显示预览区域
    };
    
    // 开始读取文件（异步操作）
    reader.readAsDataURL(file);
    
    // ============================================
    // 步骤2: 准备UI状态
    // ============================================
    resultArea.style.display = 'none';      // 隐藏之前的结果
    errorMessage.style.display = 'none';    // 隐藏错误信息
    loading.style.display = 'block';        // 显示加载动画
    
    // ============================================
    // 步骤3: 构造FormData并发送请求
    // ============================================
    const formData = new FormData();
    formData.append('file', file);  // key必须是'file'，与后端参数名对应
    
    try {
        // 发送POST请求
        const response = await fetch(`${API_BASE_URL}/api/spec-locate`, {
            method: 'POST',
            body: formData  // FormData自动设置Content-Type
        });
        
        // 解析JSON响应
        const data = await response.json();
        
        // ============================================
        // 步骤4: 处理响应
        // ============================================
        loading.style.display = 'none';  // 隐藏加载动画
        
        if (data.success) {
            displayResult(data);  // 显示识别结果
        } else {
            showError(data.message || '识别失败');
        }
        
    } catch (error) {
        // 网络错误或其他异常
        loading.style.display = 'none';
        showError('网络错误：' + error.message);
    }
}
```

#### **等价的HTTP请求**

**JavaScript Fetch:**
```javascript
fetch('http://127.0.0.1:8002/api/spec-locate', {
    method: 'POST',
    body: formData
})
```

**等价的curl命令:**
```bash
curl -X POST http://127.0.0.1:8002/api/spec-locate \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@cad_screenshot.png"
```

**HTTP请求细节:**
```http
POST /api/spec-locate HTTP/1.1
Host: 127.0.0.1:8002
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...
Content-Length: 123456

------WebKitFormBoundary...
Content-Disposition: form-data; name="file"; filename="image.png"
Content-Type: image/png

<binary image data>
------WebKitFormBoundary...--
```

---

### 4. 显示结果函数详解

#### **输入数据结构**

```javascript
// 后端返回的JSON数据结构
const data = {
    success: true,
    spec: {
        code: "12J2",         // 规范编号
        page: "C11",          // 页码
        confidence: 0.7834    // 置信度 (0-1)
    },
    file: {                   // 如果找到PDF文件
        path: "D:\\projects\\liuzong\\output_pages\\12J2\\12J2_C11.pdf",
        name: "12J2_C11.pdf",
        directory: "12J2",
        download_url: "/api/download/12J2/C11"  // ← 下载URL
    },
    candidates: [             // 候选结果（按置信度排序）
        {code: "12J2", page: "C11", confidence: 0.7834},
        {code: "12J2", page: "C12", confidence: 0.6543},
        {code: "15J401", page: "C11", confidence: 0.5432},
        // ...
    ]
}
```

#### **完整处理逻辑**

```javascript
function displayResult(data) {
    // 解构赋值，提取需要的数据
    const { spec, candidates, file } = data;
    
    // ============================================
    // A. 显示主要识别结果
    // ============================================
    document.getElementById('specCode').textContent = 
        `规范编号: ${spec.code}`;
    
    document.getElementById('pageCode').textContent = 
        `页码: ${spec.page}`;
    
    document.getElementById('confidence').textContent = 
        `置信度: ${(spec.confidence * 100).toFixed(1)}%`;
    
    // ============================================
    // B. 配置下载按钮（核心功能）
    // ============================================
    const downloadBtn = document.getElementById('downloadBtn');
    
    if (file && file.download_url) {
        // 1. 设置下载链接
        downloadBtn.href = `${API_BASE_URL}${file.download_url}`;
        // 完整URL: http://127.0.0.1:8002/api/download/12J2/C11
        
        // 2. 设置下载文件名（HTML5 download属性）
        downloadBtn.download = file.name;  // "12J2_C11.pdf"
        
        // 3. 显示按钮
        downloadBtn.style.display = 'flex';
        
        // 4. （可选）自动触发下载 - 通常不建议
        // setTimeout(() => downloadBtn.click(), 500);
        
    } else {
        // 未找到文件时隐藏下载按钮
        downloadBtn.style.display = 'none';
    }
    
    // ============================================
    // C. 显示候选结果
    // ============================================
    if (candidates && candidates.length > 1) {
        const candidatesArea = document.getElementById('candidatesArea');
        const candidatesList = document.getElementById('candidatesList');
        
        // 清空之前的内容
        candidatesList.innerHTML = '';
        
        // 遍历候选结果（跳过第1个，因为它是最佳结果）
        candidates.slice(1, 6).forEach(candidate => {
            // 创建候选项元素
            const item = document.createElement('div');
            item.className = 'candidate-item';
            item.innerHTML = `
                <div>
                    <strong>${candidate.code}</strong> - 页码: ${candidate.page}
                </div>
                <div style="color: #667eea; font-weight: bold;">
                    ${(candidate.confidence * 100).toFixed(1)}%
                </div>
            `;
            
            // 添加到列表
            candidatesList.appendChild(item);
        });
        
        // 显示候选结果区域
        candidatesArea.style.display = 'block';
    }
    
    // 显示整个结果区域
    resultArea.style.display = 'block';
}
```

#### **下载按钮的工作原理**

**HTML结构:**
```html
<a id="downloadBtn" class="download-btn" style="display: none;">
    <span>⬇️</span>
    <span>下载PDF</span>
</a>
```

**JavaScript配置后:**
```html
<a id="downloadBtn" 
   class="download-btn" 
   href="http://127.0.0.1:8002/api/download/12J2/C11"
   download="12J2_C11.pdf"
   style="display: flex;">
    <span>⬇️</span>
    <span>下载PDF</span>
</a>
```

**用户点击后的流程:**
```
1. 用户点击 <a> 标签
   ↓
2. 浏览器发起GET请求
   GET http://127.0.0.1:8002/api/download/12J2/C11
   ↓
3. 后端响应
   HTTP/1.1 200 OK
   Content-Type: application/pdf
   Content-Disposition: attachment; filename="12J2_C11.pdf"
   <PDF文件二进制数据>
   ↓
4. 浏览器触发下载
   保存为: 12J2_C11.pdf
```

---

### 5. 完整数据流向图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户操作                             │
│               (点击上传 / 拖拽文件)                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    handleFile(file)                         │
│  1. FileReader.readAsDataURL() → 显示预览                   │
│  2. 隐藏旧结果，显示加载动画                                  │
│  3. FormData.append('file', file)                           │
│  4. fetch(POST) → 发送到后端                                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTP Request
                            │ POST /api/spec-locate
                            │ Content-Type: multipart/form-data
                            │ Body: file=<image_data>
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 后端处理                          │
│  1. 接收文件 (UploadFile)                                    │
│  2. cv2.imdecode() → 解码图像                               │
│  3. OCR识别 → 提取文本                                       │
│  4. 解析规范编号和页码                                        │
│  5. FileIndex.find_file() → 查找PDF                         │
│  6. 生成 download_url                                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTP Response
                            │ 200 OK
                            │ Content-Type: application/json
                            │ Body: {success, spec, file, candidates}
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    displayResult(data)                      │
│  1. 显示规范编号: spec.code                                  │
│  2. 显示页码: spec.page                                      │
│  3. 显示置信度: spec.confidence                              │
│  4. 配置下载按钮:                                            │
│     - href = API_BASE_URL + file.download_url              │
│     - download = file.name                                 │
│  5. 显示候选结果列表                                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ (用户点击下载按钮)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     浏览器自动行为                            │
│  GET http://127.0.0.1:8002/api/download/12J2/C11           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTP Request
                            │ GET /api/download/12J2/C11
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                FastAPI 下载端点处理                          │
│  1. 解析路径参数: spec_code="12J2", page_code="C11"         │
│  2. FileIndex.find_file() → 查找PDF文件                     │
│  3. FileResponse() → 返回PDF文件                            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTP Response
                            │ 200 OK
                            │ Content-Type: application/pdf
                            │ Content-Disposition: attachment
                            │ Body: <PDF binary data>
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    浏览器下载文件                             │
│              保存为: 12J2_C11.pdf                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 关键技术点

### 1. FormData API - 文件上传

**用途：** 构造 multipart/form-data 格式的请求体，用于上传文件

```javascript
const formData = new FormData();
formData.append('file', file);  // 添加文件
formData.append('key', 'value');  // 也可以添加其他字段

fetch(url, {
    method: 'POST',
    body: formData  // 自动设置正确的Content-Type
});
```

**等价的表单提交：**
```html
<form action="/api/spec-locate" method="POST" enctype="multipart/form-data">
    <input type="file" name="file">
    <button type="submit">上传</button>
</form>
```

---

### 2. Fetch API - 现代HTTP请求

**基本用法：**
```javascript
// GET请求
fetch('http://api.example.com/data')
    .then(response => response.json())
    .then(data => console.log(data));

// POST请求
fetch('http://api.example.com/upload', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({key: 'value'})
})
    .then(response => response.json())
    .then(data => console.log(data));

// 使用 async/await（推荐）
async function getData() {
    const response = await fetch(url);
    const data = await response.json();
    return data;
}
```

**vs jQuery AJAX：**
```javascript
// Fetch API (现代)
const response = await fetch(url, {method: 'POST', body: formData});
const data = await response.json();

// jQuery AJAX (旧)
$.ajax({
    url: url,
    type: 'POST',
    data: formData,
    processData: false,
    contentType: false,
    success: function(data) { ... }
});
```

---

### 3. FileReader API - 读取文件内容

**用途：** 在浏览器中读取文件，转换为Base64或其他格式

```javascript
const reader = new FileReader();

// 读取为Base64（用于图片预览）
reader.onload = (e) => {
    img.src = e.target.result;  // data:image/png;base64,...
};
reader.readAsDataURL(file);

// 读取为文本
reader.onload = (e) => {
    console.log(e.target.result);  // 文件文本内容
};
reader.readAsText(file);

// 读取为ArrayBuffer（用于二进制处理）
reader.onload = (e) => {
    const buffer = e.target.result;
};
reader.readAsArrayBuffer(file);
```

---

### 4. HTML5 Drag & Drop API

**完整示例：**
```javascript
const dropZone = document.getElementById('dropzone');

// 1. 拖拽进入
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();  // 必须阻止默认行为
    e.dataTransfer.dropEffect = 'copy';  // 显示复制图标
});

// 2. 拖拽离开
dropZone.addEventListener('dragleave', (e) => {
    // 移除视觉效果
});

// 3. 放下文件
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();  // 阻止浏览器打开文件
    
    const files = e.dataTransfer.files;  // 获取文件列表
    if (files.length > 0) {
        handleFile(files[0]);
    }
});
```

---

### 5. `<a>` 标签的 download 属性

**功能：** 强制浏览器下载文件而不是打开

```html
<!-- 下载文件（指定文件名） -->
<a href="/files/document.pdf" download="my-document.pdf">下载</a>

<!-- 下载文件（使用原文件名） -->
<a href="/files/document.pdf" download>下载</a>

<!-- 打开文件（不下载） -->
<a href="/files/document.pdf">查看</a>
```

**JavaScript动态创建：**
```javascript
const link = document.createElement('a');
link.href = 'http://example.com/file.pdf';
link.download = 'custom-name.pdf';
document.body.appendChild(link);
link.click();  // 触发下载
document.body.removeChild(link);  // 清理
```

---

### 6. async/await - 异步编程

**Promise链式调用 vs async/await：**

```javascript
// Promise链式调用（旧风格）
fetch(url)
    .then(response => response.json())
    .then(data => {
        console.log(data);
        return processData(data);
    })
    .then(result => {
        console.log(result);
    })
    .catch(error => {
        console.error(error);
    });

// async/await（现代风格）
async function getData() {
    try {
        const response = await fetch(url);
        const data = await response.json();
        console.log(data);
        
        const result = await processData(data);
        console.log(result);
    } catch (error) {
        console.error(error);
    }
}
```

---

### 7. 错误处理策略

```javascript
async function handleFile(file) {
    try {
        // 1. 发送请求
        const response = await fetch(url, {...});
        
        // 2. 检查HTTP状态
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // 3. 解析JSON
        const data = await response.json();
        
        // 4. 检查业务逻辑
        if (data.success) {
            displayResult(data);
        } else {
            // API返回的业务错误
            showError(data.message || '识别失败');
        }
        
    } catch (error) {
        // 网络错误、超时、JSON解析错误等
        if (error.name === 'TypeError') {
            showError('网络连接失败，请检查服务器是否运行');
        } else {
            showError('错误: ' + error.message);
        }
    }
}
```

**可能的错误类型：**
| 错误类型 | 原因 | 处理方式 |
|---------|------|---------|
| `TypeError: Failed to fetch` | 网络断开/CORS/服务器未启动 | 检查服务器和网络 |
| `HTTP 400` | 请求参数错误 | 显示API返回的错误信息 |
| `HTTP 404` | 端点不存在 | 检查URL是否正确 |
| `HTTP 500` | 服务器内部错误 | 查看服务器日志 |
| `SyntaxError` | JSON解析失败 | 检查响应格式 |
| `data.success = false` | 业务逻辑错误（如识别失败） | 显示友好提示 |

---

## 总结

### **技术栈**
- **前端:** HTML5 + CSS3 + 原生JavaScript (无依赖)
- **API通信:** Fetch API + FormData
- **后端:** FastAPI + PaddleOCR
- **文件处理:** FileReader API + Blob/ArrayBuffer

### **核心优势**
1. ✅ **无需框架** - 纯原生实现，轻量高效
2. ✅ **现代API** - 使用HTML5标准API
3. ✅ **友好交互** - 拖拽上传 + 实时反馈
4. ✅ **错误处理** - 完善的异常捕获
5. ✅ **响应式设计** - 适配不同屏幕尺寸

### **可扩展性**
- 可以轻松集成到React/Vue/Angular等框架
- API调用逻辑可以封装为独立模块
- UI可以自定义为任何风格

---

## 参考资源

- [MDN - FormData](https://developer.mozilla.org/en-US/docs/Web/API/FormData)
- [MDN - Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [MDN - FileReader](https://developer.mozilla.org/en-US/docs/Web/API/FileReader)
- [MDN - Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PaddleOCR Documentation](https://github.com/PaddlePaddle/PaddleOCR)
