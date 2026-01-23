"""
豆包 Embedding 实现
支持 Vision 模型（与 load_splits.py 保持一致）
"""
import os
import concurrent.futures
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential

from langchain_core.embeddings import Embeddings
from volcenginesdkarkruntime import Ark


class DoubaoVisionEmbeddings(Embeddings):
    """豆包 Vision Embedding 模型实现（推荐使用）"""

    def __init__(self, api_key: str = None, model: str = "doubao-embedding-vision-250615"):
        """
        初始化豆包 Vision Embedding 模型

        Args:
            api_key: API 密钥，如果为 None 则从环境变量 ARK_API_KEY 读取
            model: 模型名称，默认为 Vision embedding 模型
        """
        self.client = Ark(api_key=api_key or os.environ.get("ARK_API_KEY"))
        self.model = model

    def _embed_single_text(self, text: str) -> List[float]:
        """单个文本 embedding（Vision 模型）"""
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
        """
        批量 embedding 文本（Vision 模型，使用并发）

        Args:
            texts: 文本列表

        Returns:
            embedding 向量列表
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            results = list(executor.map(self._embed_single_text, texts))
        return results

    def embed_query(self, text: str) -> List[float]:
        """
        embedding 单个查询文本（Vision 模型）

        Args:
            text: 查询文本

        Returns:
            embedding 向量
        """
        return self._embed_single_text(text)


class DoubaoEmbeddings(Embeddings):
    """豆包文本 Embedding 模型实现（备用）"""

    def __init__(self, api_key: str = None, model: str = "doubao-embedding-large-text-250515"):
        """
        初始化豆包文本 Embedding 模型

        Args:
            api_key: API 密钥，如果为 None 则从环境变量 ARK_API_KEY 读取
            model: 模型名称，默认为文本 embedding 模型
        """
        self.client = Ark(api_key=api_key or os.environ.get("ARK_API_KEY"))
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量 embedding 文本

        Args:
            texts: 文本列表

        Returns:
            embedding 向量列表
        """
        try:
            resp = self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            return [item.embedding for item in resp.data]
        except Exception as e:
            print(f"[API Error] Batch failed: {e}")
            raise e

    def embed_query(self, text: str) -> List[float]:
        """
        embedding 单个查询文本

        Args:
            text: 查询文本

        Returns:
            embedding 向量
        """
        try:
            resp = self.client.embeddings.create(
                model=self.model,
                input=[text],
                encoding_format="float"
            )
            return resp.data[0].embedding
        except Exception:
            return [0.0] * 1024

