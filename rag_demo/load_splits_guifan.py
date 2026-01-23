"""
规范库数据加载和向量索引构建
遵循 load_splits.py 的流程，保持抽象类模式
"""
import os
import json
import hashlib
import time
from typing import Set
from tqdm import tqdm

from langchain_chroma import Chroma
from langchain_core.documents import Document

from dotenv import load_dotenv
from loaders import GuiFanLoader
from embeddings import DoubaoVisionEmbeddings

load_dotenv()

# ==========================================
# 状态管理（遵循 load_splits.py 的模式）
# ==========================================
HASH_STATE_FILE = "processed_chunk_hashes_guifan.json"

def load_processed_hashes() -> Set[str]:
    """加载已处理的文档哈希"""
    if os.path.exists(HASH_STATE_FILE):
        try:
            with open(HASH_STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_processed_hashes(hashes: Set[str]):
    """保存已处理的文档哈希"""
    with open(HASH_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(hashes), f)

def compute_chunk_hash(doc: Document) -> str:
    """计算文档块的哈希值"""
    meta_copy = doc.metadata.copy()
    meta_str = json.dumps(meta_copy, sort_keys=True, ensure_ascii=False)
    raw = doc.page_content + meta_str
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


# ==========================================
# 主逻辑（遵循 load_splits.py 的流程）
# ==========================================
def build_index_stream():
    """
    使用 load_splits.py 的流程构建索引
    保持抽象类模式，但简化批处理逻辑
    """
    guifan_dir = "./data/GUIFANKU"
    persist_dir = "./chroma_db"  # 统一的数据库目录

    # 初始化加载器（抽象类模式）
    loader = GuiFanLoader(guifan_dir)

    # 初始化 Embedding 和向量库（使用 Vision 模型，与 load_splits.py 保持一致）
    doubao_emb = DoubaoVisionEmbeddings()
    vectorstore = Chroma(
        collection_name="guifan",  # 规范库专用 collection
        embedding_function=doubao_emb,
        persist_directory=persist_dir
    )

    # 加载已处理的哈希
    processed_hashes = load_processed_hashes()
    print(f">>> 已处理切片记录数: {len(processed_hashes)}")

    # --- Pass 1: 预扫描 (只计数) ---
    print(">>> 正在预扫描以计算总切片数 (Pass 1)...")
    total_chunks_count = 0
    # 这一步非常快，因为不调 Embedding API，只做本地切分
    for _ in tqdm(loader.load(), desc="Pre-scanning"):
        total_chunks_count += 1

    print(f">>> 预扫描完成，预计总切片数: {total_chunks_count}")

    # --- Pass 2: 正式处理 ---
    print(">>> 开始正式处理 (Pass 2)...")

    batch_size = 2000
    current_batch = []
    current_hashes = []

    new_chunks_count = 0
    skipped_chunks_count = 0

    # 重新创建一个生成器流（因为生成器只能遍历一次）
    loader = GuiFanLoader(guifan_dir)

    # 传入 total 参数，这样 tqdm 就能显示进度条了
    for chunk in tqdm(loader.load(), total=total_chunks_count, desc="Indexing"):
        c_hash = compute_chunk_hash(chunk)

        # 1. 跳过已处理
        if c_hash in processed_hashes:
            skipped_chunks_count += 1
            continue

        # 2. 积攒批次
        current_batch.append(chunk)
        current_hashes.append(c_hash)

        # 3. 批量写入（遵循 load_splits.py 的简单批处理）
        if len(current_batch) >= batch_size:
            try:
                vectorstore.add_documents(current_batch)
                processed_hashes.update(current_hashes)
                save_processed_hashes(processed_hashes)
                new_chunks_count += len(current_batch)
            except Exception as e:
                print(f"\n[Error] 写入批次失败: {e}")

            current_batch = []
            current_hashes = []

    # 处理尾部
    if current_batch:
        try:
            vectorstore.add_documents(current_batch)
            processed_hashes.update(current_hashes)
            save_processed_hashes(processed_hashes)
            new_chunks_count += len(current_batch)
        except Exception as e:
            print(f"\n[Error] 写入最后批次失败: {e}")

    print("\n" + "="*30)
    print("处理完成！")
    print(f"总切片数: {total_chunks_count}")
    print(f"新增入库: {new_chunks_count}")
    print(f"跳过重复: {skipped_chunks_count}")
    print(f"库中总量: {vectorstore._collection.count()}")
    print("="*30)

if __name__ == "__main__":
    time_start = time.time()
    build_index_stream()
    time_end = time.time()
    print(f"总耗时: {time_end - time_start:.2f} 秒")

