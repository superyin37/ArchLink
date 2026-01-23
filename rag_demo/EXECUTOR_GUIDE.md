# RAG 执行器框架使用指南

## 概述

`executor.py` 提供了一个抽象的 RAG 系统执行器框架，包含内置的 Rerank 模块，可以快速构建不同领域的 RAG 应用。

## 核心类

### 执行器实现

#### ConstructionRAGExecutor
建筑工程规范系统执行器，用于查询建筑规范和标准文档。

#### AnliKuRAGExecutor（旧版）
建筑案例库系统执行器（通用版本），支持自定义 Reranker。

#### AnliKuExecutor（新版）
ANLIKU 建筑案例库专用执行器，内置 SimilarityReranker，优化了文档格式化和提示词。

**特点：**
- ✅ 专门针对 ANLIKU 数据库设计
- ✅ 自动使用 DoubaoVisionEmbeddings
- ✅ 内置 SimilarityReranker（快速、高效）
- ✅ LLM 答案中包含 5 个关键字段：
  - 案例名称
  - 设计策略
  - 启示
  - 图片链接
  - 案例链接
- ✅ 建筑案例领域特定的提示词

#### GuiFanExecutor（新版）
建筑规范库专用执行器，内置 SimilarityReranker，优化了文档格式化和提示词。

**特点：**
- ✅ 专门针对 GUIFANKU 规范库设计
- ✅ 自动使用 DoubaoVisionEmbeddings
- ✅ 内置 SimilarityReranker（快速、高效）
- ✅ LLM 答案中包含 3 个关键字段：
  - 规范条款名称
  - 规范要求（原文）
  - 雷区提示（针对性建议）
- ✅ 建筑规范领域特定的提示词

### Reranker 类

#### BaseReranker（抽象基类）
所有 Reranker 的基类，定义 `rerank(query, documents, top_k)` 接口。

#### SimilarityReranker
基于向量相似度的 Reranker，使用余弦相似度重新排序文档。
- **优点**：快速、无需额外 API 调用
- **缺点**：可能不如语义理解精准

#### LLMReranker
基于 LLM 的 Reranker，使用语言模型评估文档相关性。
- **优点**：精准、理解复杂语义
- **缺点**：较慢、需要额外 API 调用

#### HybridReranker
混合 Reranker，结合多个 Reranker 的加权组合。
- **优点**：平衡速度和精准度
- **缺点**：配置复杂

### RAGExecutor（抽象基类）

提供 RAG 系统的通用框架，包括：
- 向量库初始化
- 工具定义
- Rerank 集成
- LangGraph 工作流构建
- 交互式对话循环

**需要子类实现的方法：**

1. `_format_documents(docs)` - 格式化检索到的文档
2. `_get_grade_prompt(question, context)` - 获取文档评分提示词
3. `_get_rewrite_prompt(question)` - 获取问题重写提示词
4. `_get_generate_prompt(question, context)` - 获取答案生成提示词

## 具体实现

### ConstructionRAGExecutor

用于建筑工程规范系统，特点：
- 格式化规范文档（来源、章节等）
- 建筑工程领域特定的提示词
- 专业的规范引用

### AnliKuRAGExecutor

用于建筑案例库系统，特点：
- 格式化建筑案例（项目名、类型、位置等）
- 案例分析特定的提示词
- 建筑设计特点分析

## 使用示例

### 方式 1：使用默认 Reranker（相似度）

```python
from construction_executor import ConstructionRAGExecutor
from embeddings import DoubaoVisionEmbeddings
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(...)
embedding = DoubaoVisionEmbeddings()

executor = ConstructionRAGExecutor(
    llm=llm,
    embedding_function=embedding,
    persist_dir="./chroma_db",
    collection_name="guifan"
)

executor.run()
```

### 方式 2：使用 LLM Reranker

```python
from construction_executor import ConstructionRAGExecutor
from executor import LLMReranker
from embeddings import DoubaoVisionEmbeddings
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(...)
embedding = DoubaoVisionEmbeddings()

reranker = LLMReranker(llm)

executor = ConstructionRAGExecutor(
    llm=llm,
    embedding_function=embedding,
    persist_dir="./chroma_db",
    collection_name="guifan",
    reranker=reranker,
    top_k=5
)

executor.run()
```

### 方式 3：使用混合 Reranker

```python
from construction_executor import ConstructionRAGExecutor
from executor import SimilarityReranker, LLMReranker, HybridReranker
from embeddings import DoubaoVisionEmbeddings
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(...)
embedding = DoubaoVisionEmbeddings()

reranker = HybridReranker([
    (SimilarityReranker(embedding), 0.5),
    (LLMReranker(llm), 0.5)
])

executor = ConstructionRAGExecutor(
    llm=llm,
    embedding_function=embedding,
    persist_dir="./chroma_db",
    collection_name="guifan",
    reranker=reranker,
    top_k=5
)

executor.run()
```

### 方式 4：使用 AnliKuExecutor（推荐）

```python
from anliku_executor import AnliKuExecutor
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="doubao-seed-1-6-251015",
    api_key=os.environ.get("ARK_API_KEY"),
    base_url=os.environ.get("SEED_API_BASE"),
    temperature=0.1
)

# AnliKuExecutor 已内置 SimilarityReranker 和 DoubaoVisionEmbeddings
executor = AnliKuExecutor(llm=llm)

executor.run()
```

**优点：**
- 开箱即用，无需配置 Reranker
- 自动使用 DoubaoVisionEmbeddings
- 优化的文档格式化和提示词
- 专门针对 ANLIKU 数据库优化

### 方式 5：使用 GuiFanExecutor（推荐）

```python
from guifan_executor import GuiFanExecutor
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="doubao-seed-1-6-251015",
    api_key=os.environ.get("ARK_API_KEY"),
    base_url=os.environ.get("SEED_API_BASE"),
    temperature=0.1
)

# GuiFanExecutor 已内置 SimilarityReranker 和 DoubaoVisionEmbeddings
executor = GuiFanExecutor(llm=llm)

executor.run()
```

**优点：**
- 开箱即用，无需配置 Reranker
- 自动使用 DoubaoVisionEmbeddings
- 优化的文档格式化和提示词
- 专门针对 GUIFANKU 规范库优化
- 规范要求保证原文，雷区提示针对性强

### 方式 6：创建自定义执行器

```python
from executor import RAGExecutor

class MyRAGExecutor(RAGExecutor):
    def _format_documents(self, docs):
        # 自定义文档格式化
        pass

    def _get_grade_prompt(self, question, context):
        # 自定义评分提示词
        pass

    def _get_rewrite_prompt(self, question):
        # 自定义重写提示词
        pass

    def _get_generate_prompt(self, question, context):
        # 自定义生成提示词
        pass

executor = MyRAGExecutor(...)
executor.run()
```

### 方式 6：创建自定义 Reranker

```python
from executor import BaseReranker
from langchain_core.documents import Document
from typing import List

class CustomReranker(BaseReranker):
    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Document]:
        # 自定义排序逻辑
        # 例如：基于文档长度、特定关键词等
        return documents[:top_k]

executor = ConstructionRAGExecutor(
    llm=llm,
    embedding_function=embedding,
    persist_dir="./chroma_db",
    collection_name="guifan",
    reranker=CustomReranker(),
    top_k=5
)
```

## 工作流

```
用户输入
    ↓
generate_query_or_respond (LLM 决定是否调用工具)
    ↓
[是否调用工具?]
    ├─ 是 → retrieve (检索文档)
    │        ↓
    │    grade_documents (评估文档相关性)
    │        ↓
    │    [文档相关?]
    │        ├─ 是 → generate_answer (生成答案)
    │        └─ 否 → rewrite_question (重写问题) → 回到 generate_query_or_respond
    │
    └─ 否 → 直接生成答案
```

## 配置参数

| 参数 | 说明 | 示例 | 默认值 |
|------|------|------|--------|
| llm | 语言模型实例 | ChatOpenAI(...) | 必需 |
| embedding_function | Embedding 函数 | DoubaoVisionEmbeddings() | 必需 |
| persist_dir | 向量库目录 | "./chroma_db" | 必需 |
| collection_name | Collection 名称 | "guifan", "anliku" | 必需 |
| model_name | 模型名称（显示用） | "doubao-seed-1-6-251015" | "default" |
| reranker | Reranker 实例 | SimilarityReranker(...) | SimilarityReranker |
| top_k | 返回前 k 个文档 | 5, 10 | 5 |

## 运行方式

```bash
# 使用示例程序
python main_executor.py

# 或直接使用具体实现
python -c "from construction_executor import ConstructionRAGExecutor; ..."
```

## Reranker 对比

| Reranker | 速度 | 精准度 | API 调用 | 适用场景 |
|----------|------|--------|---------|---------|
| SimilarityReranker | ⚡⚡⚡ | ⭐⭐ | 否 | 快速原型、实时应用 |
| LLMReranker | ⚡ | ⭐⭐⭐ | 是 | 精准要求高的场景 |
| HybridReranker | ⚡⚡ | ⭐⭐⭐ | 是 | 平衡速度和精准度 |

## AnliKuExecutor 详细说明

### 文档格式化（_format_documents）

AnliKuExecutor 返回的文档包含以下 5 个关键字段：

```
【案例名称】项目名称
【建筑类型】建筑分类（如科教建筑、演艺建筑）
【位置】地理位置
【年份】建成年份
【面积】建筑面积
【设计策略】从 tags 中提取的设计特点
【启示】案例的关键信息摘要
【图片链接】项目相关图片 URL 列表
【详细内容】完整的项目描述
```

### 数据来源

AnliKuExecutor 从 ANLIKU 数据库中提取数据，数据结构包括：

| 字段 | 来源 | 说明 |
|------|------|------|
| project_name | projects 表 | 项目名称 |
| topic | 目录名称 | 建筑类型（第二层文件夹名） |
| tags | project_tags 表 | 设计策略和特点 |
| images | project_images 表 | 项目图片 URL 和本地路径 |
| location | projects 表 | 地理位置 |
| year | projects 表 | 建成年份 |
| area | projects 表 | 建筑面积 |
| description | projects 表 | 项目描述 |

### 提示词特点

- **评分提示词**：评估案例与建筑类型、设计特点、地理位置的相关性
- **重写提示词**：考虑建筑类型、功能、地理位置、设计风格、年代等维度
- **生成提示词**：分析建筑类型、设计创新点、地理适应性、建筑规模、可借鉴经验

## 扩展建议

1. **添加新的执行器**：继承 `RAGExecutor` 并实现四个抽象方法
2. **添加新的 Reranker**：继承 `BaseReranker` 并实现 `rerank()` 方法
3. **自定义工作流**：覆盖 `_build_workflow()` 方法
4. **添加新的工具**：在 `_init_tools()` 中添加更多工具
5. **自定义节点逻辑**：覆盖节点方法如 `_generate_query_or_respond()`
6. **创建领域特定执行器**：参考 AnliKuExecutor 的模式为其他数据源创建专用执行器

