"""
使用执行器的示例 - 建筑工程 RAG 系统
"""
import os
from langchain_openai import ChatOpenAI
from embeddings import DoubaoVisionEmbeddings
from construction_executor import ConstructionRAGExecutor, AnliKuRAGExecutor
from anliku_executor import AnliKuExecutor
from guifan_executor import GuiFanExecutor
from executor import SimilarityReranker, LLMReranker, HybridReranker
from dotenv import load_dotenv

load_dotenv()


def create_construction_executor(reranker_type: str = "similarity"):
    """
    创建建筑工程规范 RAG 执行器

    Args:
        reranker_type: "similarity", "llm", 或 "hybrid"
    """
    llm = ChatOpenAI(
        model="doubao-seed-1-6-251015",
        api_key=os.environ.get("ARK_API_KEY"),
        base_url=os.environ.get("SEED_API_BASE"),
        temperature=0.1,
        model_kwargs={
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "stop": ["<|endoftext|>", "User:", "\nUser:", "Question:"]
        }
    )

    embedding = DoubaoVisionEmbeddings()

    # 选择 reranker
    if reranker_type == "llm":
        reranker = LLMReranker(llm)
    elif reranker_type == "hybrid":
        reranker = HybridReranker([
            (SimilarityReranker(embedding), 0.5),
            (LLMReranker(llm), 0.5)
        ])
    else:
        reranker = SimilarityReranker(embedding)

    return ConstructionRAGExecutor(
        llm=llm,
        embedding_function=embedding,
        persist_dir="./chroma_db",
        collection_name="guifan",
        model_name="doubao-seed-1-6-251015",
        reranker=reranker,
        top_k=5
    )


def create_anliku_executor(reranker_type: str = "similarity"):
    """
    创建建筑案例库 RAG 执行器

    Args:
        reranker_type: "similarity", "llm", 或 "hybrid"
    """
    llm = ChatOpenAI(
        model="doubao-seed-1-6-251015",
        api_key=os.environ.get("ARK_API_KEY"),
        base_url=os.environ.get("SEED_API_BASE"),
        temperature=0.1,
        model_kwargs={
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "stop": ["<|endoftext|>", "User:", "\nUser:", "Question:"]
        }
    )

    embedding = DoubaoVisionEmbeddings()

    # 选择 reranker
    if reranker_type == "llm":
        reranker = LLMReranker(llm)
    elif reranker_type == "hybrid":
        reranker = HybridReranker([
            (SimilarityReranker(embedding), 0.5),
            (LLMReranker(llm), 0.5)
        ])
    else:
        reranker = SimilarityReranker(embedding)

    return AnliKuRAGExecutor(
        llm=llm,
        embedding_function=embedding,
        persist_dir="./chroma_db",
        collection_name="anliku",
        model_name="doubao-seed-1-6-251015",
        reranker=reranker,
        top_k=5
    )


def main():
    """主程序"""
    print("=== 建筑工程 RAG 系统 ===\n")
    print("选择要使用的系统:")
    print("1. 建筑工程规范系统（旧版）")
    print("2. 建筑案例库系统（旧版）")
    print("3. ANLIKU 建筑案例库系统（新版）")
    print("4. 建筑规范库系统（新版）")

    choice = input("\n请选择 (1, 2, 3 或 4): ").strip()

    # 初始化 LLM（用于新版系统）
    llm_new = ChatOpenAI(
        model="doubao-seed-1-6-251015",
        api_key=os.environ.get("ARK_API_KEY"),
        base_url=os.environ.get("SEED_API_BASE"),
        frequency_penalty=0.5,
        presence_penalty=0.3,
        model_kwargs={
            "stop": ["<|endoftext|>", "User:", "\nUser:", "Question:"],
            "reasoning_effort": "medium",
        }
    )

    llm_openai = ChatOpenAI(
        model="gpt-5.1",
        base_url=os.environ.get("OPENAI_API_BASE"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        # model_kwargs={
        #     "stop": ["<|endoftext|>", "User:", "\nUser:", "Question:"]
        # }
    )

    # 新版系统不需要选择 Reranker，已内置 SimilarityReranker
    if choice == "3":
        print("\n>>> 初始化 ANLIKU 建筑案例库系统...")
        executor = AnliKuExecutor(llm=llm_openai)
        executor.run()
        return
    elif choice == "4":
        print("\n>>> 初始化建筑规范库系统...")
        executor = GuiFanExecutor(llm=llm_openai)
        executor.run()
        return

    print("\n选择 Reranker 类型:")
    print("1. 相似度 Reranker (快速)")
    print("2. LLM Reranker (精准)")
    print("3. 混合 Reranker (平衡)")

    reranker_choice = input("\n请选择 (1, 2 或 3): ").strip()
    reranker_map = {"1": "similarity", "2": "llm", "3": "hybrid"}
    reranker_type = reranker_map.get(reranker_choice, "similarity")

    if choice == "1":
        print(f"\n>>> 初始化建筑工程规范系统 (Reranker: {reranker_type})...")
        executor = create_construction_executor(reranker_type)
        executor.run()
    elif choice == "2":
        print(f"\n>>> 初始化建筑案例库系统 (Reranker: {reranker_type})...")
        executor = create_anliku_executor(reranker_type)
        executor.run()
    else:
        print("无效选择")


if __name__ == "__main__":
    main()

