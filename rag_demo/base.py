"""
基础抽象类和工具函数
"""
import os
import json
import hashlib
from abc import ABC, abstractmethod
from typing import List, Set, Generator

from langchain_core.documents import Document


# ==========================================
# 哈希工具函数
# ==========================================
def compute_chunk_hash(doc: Document) -> str:
    """计算文档块的哈希值"""
    meta_copy = doc.metadata.copy()
    meta_str = json.dumps(meta_copy, sort_keys=True, ensure_ascii=False)
    raw = doc.page_content + meta_str
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


# ==========================================
# DataLoader 抽象类
# ==========================================
class DataLoader(ABC):
    """数据加载器抽象基类"""

    @abstractmethod
    def load(self) -> Generator[Document, None, None]:
        """加载数据并生成文档流"""
        pass


# ==========================================
# DataProcessor 抽象类
# ==========================================
class DataProcessor(ABC):
    """数据处理器抽象基类"""

    def __init__(self, hash_state_file: str):
        self.hash_state_file = hash_state_file
        self.processed_hashes = self._load_processed_hashes()

    def _load_processed_hashes(self) -> Set[str]:
        """从文件加载已处理的哈希值"""
        if os.path.exists(self.hash_state_file):
            try:
                with open(self.hash_state_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    def _save_processed_hashes(self):
        """保存已处理的哈希值到文件"""
        with open(self.hash_state_file, "w", encoding="utf-8") as f:
            json.dump(list(self.processed_hashes), f)

    @abstractmethod
    def process_batch(self, batch_docs: List[Document], batch_hashes: List[str]) -> tuple:
        """处理一批文档，返回 (docs, hashes, embeddings)"""
        pass

    @abstractmethod
    def store_batch(self, batch_docs: List[Document], batch_hashes: List[str], 
                    embeddings: List[List[float]]):
        """存储处理后的批次"""
        pass

    def mark_processed(self, hashes: List[str]):
        """标记哈希值为已处理"""
        self.processed_hashes.update(hashes)
        self._save_processed_hashes()

