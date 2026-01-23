"""
executor_guifan.py
建筑规范库专用执行器
逻辑：意图识别 -> 分级检索 -> [通用 > 类型 > 地方] -> 严格JSON输出
"""
import json
from typing import List, Dict, TypedDict, Optional
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

# 引入基础组件 (假设在 executor.py 和 embeddings.py 中)
from executor import RAGExecutor, SimilarityReranker
from embeddings import DoubaoVisionEmbeddings

# --- 1. 定义 State ---
class GuiFanState(TypedDict):
    query: str
    location: str
    building_type: str
    mandatory_docs: List[Document]
    type_docs: List[Document]
    local_docs: List[Document]
    final_response: str

# --- 2. 提取器模型 ---
class QueryAnalysis(BaseModel):
    location: Optional[str] = Field(description="项目所在的城市或省份", default="")
    building_type: Optional[str] = Field(description="建筑的功能类型", default="")

class GuiFanExecutor(RAGExecutor):
    """建筑规范库 RAG 执行器 (通用优先版)"""

    def __init__(self, llm, embedding_function=None, persist_dir: str = "./chroma_db", 
                 collection_name: str = "guifan", model_name: str = "doubao-pro-32k",
                 top_k: int = 5):
        
        if embedding_function is None:
            embedding_function = DoubaoVisionEmbeddings()
        
        reranker = SimilarityReranker(embedding_function)
        
        super().__init__(
            llm=llm,
            embedding_function=embedding_function,
            persist_dir=persist_dir,
            collection_name=collection_name,
            model_name=model_name,
            reranker=reranker,
            top_k=top_k
        )

    # ============================================================
    # 核心：Prompt 定义 (已调整为 通用 > 类型 > 地方)
    # ============================================================

    def _get_generate_prompt(self, question: str, context: str, loc: str, typ: str) -> str:
        """
        构建生成提示词
        """
        return (
            "你是一个专业的建筑规范咨询专家。请基于检索到的法规库，回答设计师的问题。\n\n"
            
            "【仲裁逻辑 - 严格执行】\n"
            "请遵循以下 **优先级递减** 的顺序解决冲突：\n"
            "1. **第一优先级：通用/强条规范** (GB 55xxx / GB 50xxx)。这是国家底线，拥有最高解释权。如果其他规范与此冲突，以通用规范为准。\n"
            "2. **第二优先级：类型规范** (如{typ}规范)。针对特定功能的具体要求。在不违反通用规范的前提下，执行类型规范。\n"
            "3. **第三优先级：地方规范** (如{loc}导则)。仅作为补充参考。如果地方规范的要求低于通用或类型规范，则**无效**；如果更严格，可作为建议提出。\n\n"

            "【输出格式 - 纯 JSON】\n"
            "请直接输出一个标准的 JSON 数组，严禁 Markdown，严禁解释文字。\n"
            "JSON 结构：\n"
            "[\n"
            "  {\n"
            "    \"条款名称\": \"规范全名 + 条文编号\",\n"
            "    \"规范要求\": \"(必须是原文，不可改写)\",\n"
            "    \"雷区提示\": \"1. (冲突分析：明确指出该条款属于哪个优先级，是否覆盖了其他规范) 2. (实操建议：结合项目是'{loc}的{typ}'给出建议)\"\n"
            "  }\n"
            "]\n\n"
            
            "【严格约束】\n"
            "- 必须包含上述 3 个字段。\n"
            "- 如果在检索上下文中找不到答案，请返回空数组 []。\n"
            "- 不要编造信息。\n\n"

            f"设计师问题: {question}\n"
            f"项目背景: 地点={loc}, 类型={typ}\n\n"
            f"参考规范上下文:\n{context}"
        )

    # ============================================================
    # LangGraph 工作流
    # ============================================================

    def _build_workflow(self):
        workflow = StateGraph(GuiFanState)

        # 节点添加
        workflow.add_node("analyze_query", self._analyze_query_node)
        workflow.add_node("retrieve_mandatory", self._retrieve_mandatory_node)
        workflow.add_node("retrieve_type", self._retrieve_type_node)
        workflow.add_node("retrieve_local", self._retrieve_local_node)
        workflow.add_node("conflict_resolution", self._conflict_resolution_node)

        # 边定义
        workflow.add_edge(START, "analyze_query")
        
        # 分流
        workflow.add_edge("analyze_query", "retrieve_mandatory")
        workflow.add_edge("analyze_query", "retrieve_type")
        workflow.add_edge("analyze_query", "retrieve_local")
        
        # 汇聚
        workflow.add_edge("retrieve_mandatory", "conflict_resolution")
        workflow.add_edge("retrieve_type", "conflict_resolution")
        workflow.add_edge("retrieve_local", "conflict_resolution")
        
        workflow.add_edge("conflict_resolution", END)

        self.app = workflow.compile()

    # ============================================================
    # 节点实现
    # ============================================================

    def _analyze_query_node(self, state: GuiFanState):
        """意图分析"""
        query = state["query"]
        print(f"🧠 [Analyzer] 分析中...")
        structured_llm = self.llm.with_structured_output(QueryAnalysis)
        analysis = structured_llm.invoke(f"提取：1.地点 2.建筑类型。\n问题：{query}")
        print(f"   -> 地点: '{analysis.location}', 类型: '{analysis.building_type}'")
        return {"location": analysis.location, "building_type": analysis.building_type}

    def _retrieve_mandatory_node(self, state: GuiFanState):
        """检索通用/强条"""
        query = state["query"]
        try:
            # 尝试检索 mandatory_general 和 national_standard
            docs = self.vectorstore.similarity_search(
                query, k=3, filter={"type": "mandatory_general"}
            )
            # 补充检索国标作为兜底
            if len(docs) < 3:
                docs += self.vectorstore.similarity_search(
                    query, k=2, filter={"type": "national_standard"}
                )
        except:
            docs = []
        return {"mandatory_docs": docs}

    def _retrieve_type_node(self, state: GuiFanState):
        """检索类型规范"""
        query = state["query"]
        b_type = state["building_type"]
        if not b_type: return {"type_docs": []}
        
        # 简单检索 + 过滤
        docs = self.vectorstore.similarity_search(query, k=4)
        filtered = [d for d in docs if b_type in d.metadata.get('doc_name', '')]
        return {"type_docs": filtered if filtered else docs[:2]}

    def _retrieve_local_node(self, state: GuiFanState):
        """检索地方规范"""
        query = state["query"]
        loc = state["location"]
        if not loc: return {"local_docs": []}
        
        try:
            # 构造带地点的查询
            docs = self.vectorstore.similarity_search(
                f"{loc} {query}", k=3, filter={"type": "local_guide"}
            )
            # 二次确认文档名包含地点
            final_docs = [d for d in docs if loc in d.metadata.get('doc_name', '')]
        except:
            final_docs = []
        return {"local_docs": final_docs}

    def _conflict_resolution_node(self, state: GuiFanState):
        """仲裁与生成"""
        print(f"⚖️ [Arbiter] 正在根据 [通用>类型>地方] 逻辑生成...")
        
        mandatory = state.get("mandatory_docs", [])
        type_docs = state.get("type_docs", [])
        local_docs = state.get("local_docs", [])
        
        query = state["query"]
        loc = state["location"]
        typ = state["building_type"]

        # 格式化上下文
        context_str = self._format_docs_for_arbitration(mandatory, type_docs, local_docs, loc, typ)
        # 获取 Prompt
        prompt_text = self._get_generate_prompt(query, context_str, loc, typ)
        
        response = self.llm.invoke(prompt_text)
        content = response.content.strip()

        # JSON 清洗
        if content.startswith("```json"): content = content[7:]
        if content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]
        
        return {"final_response": content.strip()}

    # ============================================================
    # 辅助方法 (文档排序已调整)
    # ============================================================

    def _format_docs_for_arbitration(self, mandatory, typed, local, loc, typ) -> str:
        """
        按照 通用 -> 类型 -> 地方 的顺序拼接文档，方便 LLM 认知优先级
        """
        formatted = []
        
        # 1. 通用/强条 (最高优先级)
        formatted.append("🔴 【第一优先级：通用/强制性规范】(国家底线，必须遵守)")
        if mandatory:
            for i, d in enumerate(mandatory):
                formatted.append(f"   [{i+1}] 《{d.metadata.get('doc_name')}》: {d.page_content.strip()}")
        else:
            formatted.append("   (未检索到相关强条)")

        # 2. 类型规范
        formatted.append(f"\n🔵 【第二优先级：{typ} 类型规范】(功能性要求)")
        if typed:
            for i, d in enumerate(typed):
                formatted.append(f"   [{i+1}] 《{d.metadata.get('doc_name')}》: {d.page_content.strip()}")
        else:
            formatted.append(f"   (未检索到 {typ} 专属规范)")

        # 3. 地方规范
        formatted.append(f"\n🟢 【第三优先级：{loc} 地方规范】(补充参考)")
        if local:
            for i, d in enumerate(local):
                formatted.append(f"   [{i+1}] 《{d.metadata.get('doc_name')}》: {d.page_content.strip()}")
        else:
            formatted.append(f"   (未检索到 {loc} 地方导则)")
        
        return "\n".join(formatted)

    # 占位符
    def _format_documents(self, docs): return ""
    def _get_rewrite_prompt(self, q): return q
    def _get_grade_prompt(self, q, c): return "yes"

    def run(self):
        print(f"\n>>> 建筑规范查询系统 (Model: {self.model_name})")
        print(">>> 逻辑: 意图 -> [通用>类型>地方] -> JSON")
        
        while True:
            try:
                user_input = input("\nUser: ")
                if user_input.lower() in ["q", "quit", "exit"]: break
                result = self.app.invoke({"query": user_input})
                
                try:
                    data = json.loads(result['final_response'])
                    print(f"\nAssistant (JSON):\n{json.dumps(data, indent=2, ensure_ascii=False)}\n")
                except:
                    print(f"\nAssistant (Raw):\n{result['final_response']}\n")
            except Exception as e:
                print(f"[Error] {e}")