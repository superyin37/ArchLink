"""
抽象执行器 - 用于构建 RAG 系统的通用框架
"""
import os
import math
from abc import ABC, abstractmethod
from typing import List, Optional
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
from langchain_core.documents import Document
from langchain_core.tools import tool
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field


class BaseReranker(ABC):
    """Rerank 基类"""

    @abstractmethod
    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Document]:
        """重新排序文档"""
        pass


class SimilarityReranker(BaseReranker):
    """基于相似度的 Reranker"""

    def __init__(self, embedding_function):
        self.embedding_function = embedding_function

    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Document]:
        """使用相似度重新排序文档"""
        if not documents:
            return []

        query_embedding = self.embedding_function.embed_query(query)
        scores = []

        for doc in documents:
            doc_embedding = self.embedding_function.embed_query(doc.page_content)
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            scores.append((doc, similarity))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in scores[:top_k]]

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class LLMReranker(BaseReranker):
    """基于 LLM 的 Reranker"""

    def __init__(self, llm):
        self.llm = llm

    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Document]:
        """使用 LLM 重新排序文档"""
        if not documents:
            return []

        doc_texts = "\n\n".join([
            f"[文档 {i+1}]\n{doc.page_content[:200]}..."
            for i, doc in enumerate(documents)
        ])

        prompt = (
            f"请根据与查询的相关性，对以下文档进行排序。\n\n"
            f"查询: {query}\n\n"
            f"文档列表:\n{doc_texts}\n\n"
            f"请按相关性从高到低排序，只输出文档编号，用逗号分隔。\n"
            f"例如: 2,1,3"
        )

        response = self.llm.invoke(prompt)

        try:
            order = [int(x.strip()) - 1 for x in response.content.split(',')]
            reranked = [documents[i] for i in order if 0 <= i < len(documents)]
            return reranked[:top_k]
        except Exception:
            return documents[:top_k]


class HybridReranker(BaseReranker):
    """混合 Reranker - 结合多个 Reranker"""

    def __init__(self, rerankers: List[tuple]):
        """
        Args:
            rerankers: [(reranker, weight), ...] 列表
        """
        self.rerankers = rerankers
        total_weight = sum(w for _, w in rerankers)
        self.weights = [w / total_weight for _, w in rerankers]

    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Document]:
        """使用多个 Reranker 的加权组合"""
        if not documents:
            return []

        scores = {i: 0.0 for i in range(len(documents))}

        for (reranker, _), weight in zip(self.rerankers, self.weights):
            reranked = reranker.rerank(query, documents, top_k=len(documents))
            for rank, doc in enumerate(reranked):
                score = 1.0 / (rank + 1)
                doc_idx = documents.index(doc)
                scores[doc_idx] += score * weight

        sorted_indices = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
        return [documents[i] for i in sorted_indices[:top_k]]


class RAGExecutor(ABC):
    """RAG 系统执行器基类"""

    def __init__(
        self,
        llm,
        embedding_function,
        persist_dir: str,
        collection_name: str,
        model_name: str = "default",
        reranker: Optional[BaseReranker] = None,
        top_k: int = 5
    ):
        """
        初始化执行器

        Args:
            llm: 语言模型实例
            embedding_function: Embedding 函数
            persist_dir: 向量库目录
            collection_name: Collection 名称
            model_name: 模型名称（用于显示）
            reranker: Reranker 实例（可选）
            top_k: 返回前 k 个文档
        """
        self.llm = llm
        self.embedding_function = embedding_function
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.model_name = model_name
        self.reranker = reranker or SimilarityReranker(embedding_function)
        self.top_k = top_k

        self._init_vectorstore()
        self._init_tools()
        self._build_workflow()

    def _init_vectorstore(self):
        """初始化向量库"""
        if not os.path.exists(self.persist_dir):
            raise ValueError(f"向量库目录不存在: {self.persist_dir}")
        
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
            persist_directory=self.persist_dir
        )
        self.retriever = self.vectorstore.as_retriever()

    def _init_tools(self):
        """初始化工具"""
        @tool
        def retrieve_documents(query: str):
            """检索相关文档"""
            docs = self.retriever.invoke(query)
            # 使用 reranker 重新排序
            reranked_docs = self.reranker.rerank(query, docs, top_k=self.top_k)
            return self._format_documents(reranked_docs)

        self.tools = [retrieve_documents]

    @abstractmethod
    def _format_documents(self, docs: List) -> str:
        """格式化文档 - 子类实现"""
        pass

    @abstractmethod
    def _get_grade_prompt(self, question: str, context: str) -> str:
        """获取评分提示词 - 子类实现"""
        pass

    @abstractmethod
    def _get_rewrite_prompt(self, question: str) -> str:
        """获取重写提示词 - 子类实现"""
        pass

    @abstractmethod
    def _get_generate_prompt(self, question: str, context: str) -> str:
        """获取生成提示词 - 子类实现"""
        pass

    def _build_workflow(self):
        """构建 LangGraph 工作流"""
        workflow = StateGraph(MessagesState)
        
        workflow.add_node("generate_query_or_respond", self._generate_query_or_respond)
        workflow.add_node("retrieve", ToolNode(self.tools))
        workflow.add_node("rewrite_question", self._rewrite_question)
        workflow.add_node("generate_answer", self._generate_answer)
        
        workflow.add_edge(START, "generate_query_or_respond")
        workflow.add_conditional_edges(
            "generate_query_or_respond",
            tools_condition,
            {"tools": "retrieve", END: END},
        )
        workflow.add_conditional_edges("retrieve", self._grade_documents)
        workflow.add_edge("generate_answer", END)
        workflow.add_edge("rewrite_question", "generate_query_or_respond")
        
        self.app = workflow.compile()

    def _generate_query_or_respond(self, state: MessagesState):
        """LLM 决定是否调用工具"""
        llm_with_tools = self.llm.bind_tools(self.tools)
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def _grade_documents(self, state: MessagesState):
        """评估检索文档的相关性"""
        messages = state["messages"]
        last_message = messages[-1]
        question = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
        context = last_message.content
        
        prompt = self._get_grade_prompt(question, context)
        
        from pydantic import BaseModel, Field
        
        class GradeDocuments(BaseModel):
            binary_score: str = Field(description="'yes' or 'no'")
        
        structured_llm = self.llm.with_structured_output(GradeDocuments)
        response = structured_llm.invoke(prompt)
        
        return "generate_answer" if response.binary_score == "yes" else "rewrite_question"

    def _rewrite_question(self, state: MessagesState):
        """重写问题"""
        messages = state["messages"]
        question = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
        
        prompt = self._get_rewrite_prompt(question)
        response = self.llm.invoke(prompt)
        return {"messages": [HumanMessage(content=response.content)]}

    def _generate_answer(self, state: MessagesState):
        """生成最终答案"""
        messages = state["messages"]
        question = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
        context = next((m.content for m in reversed(messages) if m.type == 'tool'), "")
        
        prompt = self._get_generate_prompt(question, context)
        response = self.llm.invoke(prompt)
        return {"messages": [response]}

    def run(self):
        """运行交互式对话"""
        print(f"\n>>> RAG 系统 (Model: {self.model_name})")
        print(">>> 请输入问题 (输入 'q' 退出):")
        
        while True:
            try:
                user_input = input("\nUser: ")
            except EOFError:
                break
            
            if user_input.lower() in ["q", "quit", "exit"]:
                break
            
            initial_state = {"messages": [HumanMessage(content=user_input)]}
            
            try:
                for chunk in self.app.stream(initial_state):
                    pass
                
                final_state = chunk
                last_node = list(final_state.keys())[0]
                last_msg = final_state[last_node]["messages"][-1]
                print(f"\nAssistant: {last_msg.content}")
                
            except Exception as e:
                print(f"\n[Error] 执行出错: {e}")

