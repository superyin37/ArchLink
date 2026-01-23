"""
查询示例：展示如何从不同的 collection 中查询数据
"""
from langchain_chroma import Chroma
from embeddings import DoubaoVisionEmbeddings
from dotenv import load_dotenv

load_dotenv()

# 初始化 Embedding（使用 Vision 模型，与 load_splits.py 保持一致）
doubao_emb = DoubaoVisionEmbeddings()

# 统一的数据库目录
persist_dir = "./chroma_db"

# ==========================================
# 查询规范库
# ==========================================
print("=== 查询规范库 (guifan) ===")
vectorstore_guifan = Chroma(
    collection_name="guifan",
    embedding_function=doubao_emb,
    persist_directory=persist_dir
)

# 查询示例
query = "住宅设计规范中关于层高的要求"
results = vectorstore_guifan.similarity_search(query, k=3)

print(f"查询: {query}")
print(f"找到 {len(results)} 个相关文档\n")
for i, doc in enumerate(results, 1):
    print(f"结果 {i}:")
    print(f"  文档名: {doc.metadata.get('doc_name', 'N/A')}")
    print(f"  内容预览: {doc.page_content[:100]}...")
    print()

# ==========================================
# 查询案例库
# ==========================================
print("\n=== 查询案例库 (cases) ===")
vectorstore_cases = Chroma(
    collection_name="cases",
    embedding_function=doubao_emb,
    persist_directory=persist_dir
)

query = "绿色建筑案例"
results = vectorstore_cases.similarity_search(query, k=3)

print(f"查询: {query}")
print(f"找到 {len(results)} 个相关文档\n")
for i, doc in enumerate(results, 1):
    print(f"结果 {i}:")
    print(f"  案例名: {doc.metadata.get('case_name', 'N/A')}")
    print(f"  内容预览: {doc.page_content[:100]}...")
    print()

# ==========================================
# 查询原始数据
# ==========================================
print("\n=== 查询原始数据 (data) ===")
vectorstore_data = Chroma(
    collection_name="data",
    embedding_function=doubao_emb,
    persist_directory=persist_dir
)

query = "建筑设计"
results = vectorstore_data.similarity_search(query, k=3)

print(f"查询: {query}")
print(f"找到 {len(results)} 个相关文档\n")
for i, doc in enumerate(results, 1):
    print(f"结果 {i}:")
    print(f"  文档名: {doc.metadata.get('doc_name', 'N/A')}")
    print(f"  内容预览: {doc.page_content[:100]}...")
    print()

# ==========================================
# 统计信息
# ==========================================
print("\n=== 数据库统计信息 ===")
print(f"规范库文档数: {vectorstore_guifan._collection.count()}")
print(f"案例库文档数: {vectorstore_cases._collection.count()}")
print(f"原始数据文档数: {vectorstore_data._collection.count()}")
print(f"总文档数: {vectorstore_guifan._collection.count() + vectorstore_cases._collection.count() + vectorstore_data._collection.count()}")

