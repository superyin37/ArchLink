"""
数据处理器实现
"""
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document

from base import DataProcessor
from embeddings import DoubaoEmbeddings


class ChromaProcessor(DataProcessor):
    """使用 Chroma 向量库处理和存储文档"""

    def __init__(self, hash_state_file: str, embedder: DoubaoEmbeddings,
                 collection_name: str, persist_dir: str):
        """
        初始化 Chroma 处理器
        
        Args:
            hash_state_file: 哈希状态文件路径
            embedder: Embedding 模型实例
            collection_name: Chroma 集合名称
            persist_dir: Chroma 持久化目录
        """
        super().__init__(hash_state_file)
        self.embedder = embedder
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embedder,
            persist_directory=persist_dir
        )

    def process_batch(self, batch_docs: List[Document], batch_hashes: List[str]) -> tuple:
        """
        处理一批文档，生成 embeddings
        
        Args:
            batch_docs: 文档列表
            batch_hashes: 对应的哈希值列表
            
        Returns:
            tuple: (docs, hashes, embeddings)
        """
        texts = [d.page_content for d in batch_docs]
        embeddings = self.embedder.embed_documents(texts)
        return batch_docs, batch_hashes, embeddings

    def store_batch(self, batch_docs: List[Document], batch_hashes: List[str],
                    embeddings: List[List[float]]):
        """
        存储批次到 Chroma
        
        Args:
            batch_docs: 文档列表
            batch_hashes: 哈希值列表
            embeddings: embedding 向量列表
        """
        self.vectorstore._collection.upsert(
            ids=batch_hashes,
            embeddings=embeddings,
            documents=[d.page_content for d in batch_docs],
            metadatas=[d.metadata for d in batch_docs]
        )
        self.mark_processed(batch_hashes)

    def get_collection_count(self) -> int:
        """获取集合中的文档数量"""
        return self.vectorstore._collection.count()

