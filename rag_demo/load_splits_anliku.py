"""
ANLIKU 建筑案例库索引构建
"""
import os
import json
import hashlib
from typing import Set
from tqdm import tqdm

from langchain_chroma import Chroma
from langchain_core.documents import Document

from loaders import AnliKuLoader
from embeddings import DoubaoVisionEmbeddings
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 状态管理
# ==========================================
HASH_STATE_FILE = "processed_chunk_hashes_anliku.json"

def load_processed_hashes() -> Set[str]:
    if os.path.exists(HASH_STATE_FILE):
        try:
            with open(HASH_STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_processed_hashes(hashes: Set[str]):
    with open(HASH_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(hashes), f, ensure_ascii=False, indent=2)

def compute_chunk_hash(doc: Document) -> str:
    meta_copy = doc.metadata.copy()
    meta_str = json.dumps(meta_copy, sort_keys=True, ensure_ascii=False)
    raw = doc.page_content + meta_str
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

# ==========================================
# 主程序
# ==========================================
def build_index_stream():
    anliku_dir = "./data/ANLIKU"
    persist_dir = "./chroma_db"

    loader = AnliKuLoader(anliku_dir)

    doubao_emb = DoubaoVisionEmbeddings()
    vectorstore = Chroma(
        collection_name="anliku",
        embedding_function=doubao_emb,
        persist_directory=persist_dir
    )

    processed_hashes = load_processed_hashes()

    # Pass 1: 预扫描，计算总数
    print("Pass 1: 预扫描文档...")
    total_count = 0
    for _ in tqdm(loader.load(), desc="Pre-scanning"):
        total_count += 1

    # Pass 2: 处理并写入
    print(f"\nPass 2: 处理 {total_count} 个文档块...")
    loader = AnliKuLoader(anliku_dir)

    batch_size = 2000
    current_batch = []
    new_hashes = set()

    for doc in tqdm(loader.load(), total=total_count, desc="Indexing"):
        doc_hash = compute_chunk_hash(doc)

        if doc_hash in processed_hashes:
            continue

        current_batch.append(doc)
        new_hashes.add(doc_hash)

        if len(current_batch) >= batch_size:
            vectorstore.add_documents(current_batch)
            current_batch = []

    if current_batch:
        vectorstore.add_documents(current_batch)

    processed_hashes.update(new_hashes)
    save_processed_hashes(processed_hashes)

    print(f"\n✓ 完成！新增 {len(new_hashes)} 个文档块")
    print(f"✓ 总处理 {len(processed_hashes)} 个文档块")

if __name__ == "__main__":
    build_index_stream()

