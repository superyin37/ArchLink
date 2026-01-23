# 建筑 RAG 系统使用指南

本项目提供了建筑案例库和规范库的 RAG（检索增强生成）系统，支持智能检索和问答。

## 目录

- [快速开始](#快速开始)
- [数据加载](#数据加载)
- [运行查询系统](#运行查询系统)
- [数据管理](#数据管理)
- [常见问题](#常见问题)

---

## 快速开始

### 1. 环境配置

确保已安装依赖：
```bash
uv sync
```

配置环境变量（`.env` 文件）：
```env
ARK_API_KEY=your_api_key
SEED_API_BASE=your_api_base_url
```

### 2. 完整流程

```bash
# 1. 加载数据到向量库
uv run load_splits_anliku.py   # 加载案例库
uv run load_splits_guifan.py   # 加载规范库

# 2. 运行查询系统
uv run main_executor.py

# 3. 如需清理数据
uv run delete_collection.py
```

---

## 数据加载

### 案例库加载

**脚本：** `load_splits_anliku.py`

**数据源：** `./ANLIKU` 目录（SQLite 数据库）

**功能：**
- 从 ANLIKU 数据库提取建筑案例数据
- 包含项目名称、类型、位置、年份、面积、描述、标签、图片、项目链接等
- 自动分块并生成向量索引
- 增量更新（只处理新增或修改的数据）

**使用方法：**
```bash
uv run load_splits_anliku.py
```

**输出：**
- 向量库：`./chroma_db/` (collection: `anliku`)
- 状态文件：`processed_chunk_hashes_anliku.json`

**预期输出示例：**
```
Pass 1: 预扫描文档...
Pre-scanning: 100%|████████████| 1234/1234

Pass 2: 处理 1234 个文档块...
Indexing: 100%|████████████| 1234/1234

✓ 完成！新增 1234 个文档块
✓ 总处理 1234 个文档块
```

---

### 规范库加载

**脚本：** `load_splits_guifan.py`

**数据源：** `./GUIFANKU` 目录（Markdown 文件）

**功能：**
- 从规范库文件夹读取 Markdown 格式的规范文档
- 按标题层级自动分割
- 支持元数据（meta.json）
- 增量更新

**使用方法：**
```bash
uv run load_splits_guifan.py
```

**输出：**
- 向量库：`./chroma_db/` (collection: `guifan`)
- 状态文件：`processed_chunk_hashes_guifan.json`

---

### 重新加载数据

如果数据源有更新，直接重新运行加载脚本即可：
```bash
# 增量更新（推荐）
uv run load_splits_anliku.py

# 或完全重建（先删除再加载）
uv run delete_collection.py  # 选择对应的 collection
uv run load_splits_anliku.py
```

---

## 运行查询系统

**脚本：** `main_executor.py`

**功能：**
- 交互式问答系统
- 支持案例库和规范库查询
- 智能检索和重排序
- 多维度案例分析（功能、材质、场地）

### 使用方法

```bash
uv run main_executor.py
```

### 交互界面

```
请选择系统:
1. 建筑工程规范系统 (GuiFan)
2. 建筑案例库系统 (AnliKu - 旧版)
3. ANLIKU 建筑案例库系统 (新版 - 推荐)
请选择 (1, 2, 3 或 4): 3

>>> 初始化 ANLIKU 建筑案例库系统...
>>> RAG 系统 (Model: doubao-seed-1-6-251015)
>>> 请输入问题 (输入 'q' 退出):

User: 我要设计一个现代办公建筑，需要开放式平面布局
```

### 系统选项说明

**选项 1：建筑工程规范系统**
- 查询建筑规范和标准
- 返回规范条款、要求和建议
- 适合：规范查询、合规检查

**选项 2：建筑案例库系统（旧版）**
- 通用案例检索
- 基础功能

**选项 3：ANLIKU 建筑案例库系统（新版 - 推荐）**
- 多维度智能检索（功能、材质、场地）
- 并行跨界联想
- 自动评分和查询优化
- 返回 JSON 格式的案例分析
- 适合：设计参考、案例研究

### 查询示例

**案例库查询：**
```
User: 我现在要在天津大学卫津路校区西门盖个剧场，给我相关参考案例
User: 现代办公建筑的开放式平面设计
User: 红砖立面的文化建筑
User: 山地建筑的场地处理策略
```

**规范库查询：**
```
User: 住宅建筑的层高要求
User: 剧场建筑的防火规范
User: 无障碍设计的坡道要求
```

### 退出系统

输入 `q`、`quit` 或 `exit` 退出

---

## 数据管理

**脚本：** `delete_collection.py`

**功能：**
- 交互式删除向量库数据
- 支持单独删除或全部删除
- 自动清理状态文件

### 使用方法

```bash
uv run delete_collection.py
```

### 交互界面

```
============================================================
Chroma Collection 删除工具
============================================================

请选择要删除的 collection:
1. 案例库 (anliku)
2. 规范库 (guifan)
3. 全部删除（包括向量库目录）
0. 取消

请输入选项 (0-3):
```

### 选项说明

| 选项 | 功能 | 删除内容 | 后续操作 |
|------|------|----------|----------|
| 1 | 删除案例库 | `anliku` collection + 状态文件 | `uv run load_splits_anliku.py` |
| 2 | 删除规范库 | `guifan` collection + 状态文件 | `uv run load_splits_guifan.py` |
| 3 | 全部删除 | 整个 `./chroma_db` 目录 + 所有状态文件 | 重新加载所有数据 |
| 0 | 取消 | 无 | - |

**注意：** 选项 3 需要二次确认（输入 `yes` 或 `y`）

---

## 常见问题

### 1. 数据加载很慢？

**原因：** 首次加载需要生成所有向量
**解决：** 
- 首次加载耐心等待
- 后续使用增量更新，速度很快

### 2. 查询结果不理想？

**解决方法：**
- 使用更具体的描述
- 尝试不同的关键词
- 系统会自动重写查询并重试

### 3. 如何更新数据？

**方法 1：增量更新（推荐）**
```bash
uv run load_splits_anliku.py
```

**方法 2：完全重建**
```bash
uv run delete_collection.py  # 选择对应 collection
uv run load_splits_anliku.py
```

### 4. 向量库占用空间太大？

**解决：**
```bash
# 删除不需要的 collection
uv run delete_collection.py
```

### 5. 如何查看已有数据？

**方法：**
```python
# 使用 query_example.py
uv run query_example.py
```

---

## 文件说明

| 文件 | 功能 |
|------|------|
| `load_splits_anliku.py` | 案例库数据加载 |
| `load_splits_guifan.py` | 规范库数据加载 |
| `main_executor.py` | 交互式查询系统 |
| `delete_collection.py` | 数据删除工具 |
| `anliku_executor.py` | 案例库执行器（新版） |
| `guifan_executor.py` | 规范库执行器 |
| `loaders.py` | 数据加载器 |
| `embeddings.py` | Embedding 模型 |
| `executor.py` | RAG 执行器基类 |

---

## 技术架构

- **向量数据库：** ChromaDB
- **Embedding 模型：** 豆包 Vision Embedding (doubao-embedding-vision-250615)
- **LLM 模型：** 豆包 Seed (doubao-seed-1-6-251015)
- **框架：** LangChain + LangGraph
- **数据源：** SQLite (案例库) + Markdown (规范库)

---

## 更多信息

详细的技术文档请参考：
- `EXECUTOR_GUIDE.md` - 执行器框架使用指南
- `README.md` - 项目总体说明

