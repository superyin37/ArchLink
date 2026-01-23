import os
import json
import hashlib
import concurrent.futures
from typing import List, Dict, Set, Generator, Iterable
from tqdm import tqdm

# LangChain Imports
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from volcenginesdkarkruntime import Ark

from dotenv import load_dotenv
load_dotenv()

# ==========================================
# 1. 自定义豆包 Embedding 类 (保持不变)
# ==========================================
class DoubaoVisionEmbeddings(Embeddings):
    def __init__(self, api_key: str = None, model: str = "doubao-embedding-vision-250615"):
        self.client = Ark(api_key=api_key or os.environ.get("ARK_API_KEY"))
        self.model = model

    def _embed_single_text(self, text: str) -> List[float]:
        try:
            resp = self.client.multimodal_embeddings.create(
                model=self.model,
                encoding_format="float",
                input=[{"type": "text", "text": text}]
            )
            return resp.data.embedding
        except Exception:
            return [0.0] * 1024 

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(self._embed_single_text, texts))
        return results

    def embed_query(self, text: str) -> List[float]:
        return self._embed_single_text(text)

# ==========================================
# 2. 状态管理
# ==========================================
HASH_STATE_FILE = "processed_chunk_hashes.json"

def load_processed_hashes() -> Set[str]:
    if os.path.exists(HASH_STATE_FILE):
        try:
            with open(HASH_STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_processed_hashes(hashes: Set[str]):
    with open(HASH_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(hashes), f)

def compute_chunk_hash(doc: Document) -> str:
    meta_copy = doc.metadata.copy()
    meta_str = json.dumps(meta_copy, sort_keys=True, ensure_ascii=False)
    raw = doc.page_content + meta_str
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

# ==========================================
# 3. 流式生成器 (封装为函数以便重复调用)
# ==========================================

def get_chunk_stream(root_dir: str) -> Generator[Document, None, None]:
    """
    组合函数：从磁盘读取 -> 结构化切分 -> 长度切分 -> 产出切片
    每次调用都会返回一个新的生成器对象
    """
    
    # 内部生成器：读取文件
    def _file_generator():
        if not os.path.exists(root_dir):
            return
        for folder_name in os.listdir(root_dir):
            folder_path = os.path.join(root_dir, folder_name)
            if not os.path.isdir(folder_path): continue
            
            md_file_path = os.path.join(folder_path, f"{folder_name}.md")
            if not os.path.exists(md_file_path):
                md_files = [f for f in os.listdir(folder_path) if f.endswith(".md")]
                if md_files: md_file_path = os.path.join(folder_path, md_files[0])
                else: continue
            
            try:
                with open(md_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except: continue

            base_name = os.path.splitext(os.path.basename(md_file_path))[0]
            meta_file_path = os.path.join(folder_path, f"{base_name}_meta.json")
            metadata = {"source": os.path.abspath(md_file_path), "doc_name": folder_name}
            
            if os.path.exists(meta_file_path):
                try:
                    with open(meta_file_path, "r", encoding="utf-8") as f:
                        json_meta = json.load(f)
                        for k, v in json_meta.items():
                            if isinstance(v, (list, dict)):
                                metadata[k] = json.dumps(v, ensure_ascii=False)
                            else:
                                metadata[k] = v
                except: pass
            
            yield Document(page_content=content, metadata=metadata)

    # 内部逻辑：切分
    docs_stream = _file_generator()
    headers = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)

    for doc in docs_stream:
        header_splits = markdown_splitter.split_text(doc.page_content)
        for split in header_splits:
            split.metadata.update(doc.metadata)
        final_chunks = text_splitter.split_documents(header_splits)
        for chunk in final_chunks:
            yield chunk

# ==========================================
# 4. 主逻辑
# ==========================================

def build_index_stream():
    data_dir = "./data"
    persist_dir = "./chroma_db"  # 统一的数据库目录

    doubao_emb = DoubaoVisionEmbeddings()
    vectorstore = Chroma(
        collection_name="data",  # 原始数据专用 collection
        embedding_function=doubao_emb,
        persist_directory=persist_dir
    )
    
    processed_hashes = load_processed_hashes()
    print(f">>> 已处理切片记录数: {len(processed_hashes)}")
    
    # --- Pass 1: 预扫描 (只计数) ---
    print(">>> 正在预扫描以计算总切片数 (Pass 1)...")
    total_chunks_count = 0
    # 这一步非常快，因为不调 Embedding API，只做本地切分
    for _ in tqdm(get_chunk_stream(data_dir), desc="Pre-scanning"):
        total_chunks_count += 1
        
    print(f">>> 预扫描完成，预计总切片数: {total_chunks_count}")

    # --- Pass 2: 正式处理 ---
    print(">>> 开始正式处理 (Pass 2)...")
    
    batch_size = 1000
    current_batch = []
    current_hashes = []
    
    new_chunks_count = 0
    skipped_chunks_count = 0
    
    # 重新创建一个生成器流
    chunk_stream = get_chunk_stream(data_dir)
    
    # 传入 total 参数，这样 tqdm 就能显示进度条了
    for chunk in tqdm(chunk_stream, total=total_chunks_count, desc="Indexing"):
        c_hash = compute_chunk_hash(chunk)
        
        # 1. 跳过已处理
        if c_hash in processed_hashes:
            skipped_chunks_count += 1
            continue
            
        # 2. 积攒批次
        current_batch.append(chunk)
        current_hashes.append(c_hash)
        
        # 3. 批量写入
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
    print(f"处理完成！")
    print(f"总切片数: {total_chunks_count}")
    print(f"新增入库: {new_chunks_count}")
    print(f"跳过重复: {skipped_chunks_count}")
    print(f"库中总量: {vectorstore._collection.count()}")
    print("="*30)

if __name__ == "__main__":
    build_index_stream()