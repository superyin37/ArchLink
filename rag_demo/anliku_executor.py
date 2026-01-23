import json
import operator
from typing import List, Dict, Annotated, TypedDict, Union
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

# 保持原有的引用
from executor import RAGExecutor, SimilarityReranker
from embeddings import DoubaoVisionEmbeddings

# --- 1. 定义 State ---
# 使用 operator.add 实现并行节点结果的自动合并
class DesignState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    original_query: str
    sub_queries: Dict[str, str]  # 存储拆解后的三个维度查询词
    retrieved_docs: Annotated[List[Document], operator.add]  # 并行节点的文档会自动 append 到此列表
    unique_docs: List[Document]  # 聚合去重后的文档
    relevance_score: float
    retry_count: int
    # 保存第一次检索的结果，用于对比
    first_attempt_docs: List[Document]
    first_attempt_score: float

class AnliKuExecutor(RAGExecutor):
    """
    ANLIKU 架构师专用执行器 - 方案一：并行跨界联想流
    """

    def __init__(self, llm, embedding_function=None, persist_dir: str = "./chroma_db",
                 collection_name: str = "anliku", model_name: str = "doubao-seed-1-6-251015",
                 top_k: int = 5, min_cases: int = 4):
        
        if embedding_function is None:
            embedding_function = DoubaoVisionEmbeddings()

        reranker = SimilarityReranker(embedding_function)
        self.min_cases = min_cases

        super().__init__(
            llm=llm,
            embedding_function=embedding_function,
            persist_dir=persist_dir,
            collection_name=collection_name,
            model_name=model_name,
            reranker=reranker,
            top_k=top_k
        )

    # --- 2. 核心工作流构建 ---
    def _build_workflow(self):
        """构建并行跨界搜索工作流"""
        workflow = StateGraph(DesignState)

        # 添加节点
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("retrieve_function", self._retrieve_function_node)
        workflow.add_node("retrieve_material", self._retrieve_material_node)
        workflow.add_node("retrieve_site", self._retrieve_site_node)
        workflow.add_node("aggregator", self._aggregator_node)
        workflow.add_node("grader", self._grader_node)
        workflow.add_node("rewriter", self._rewriter_node)
        workflow.add_node("generator", self._generator_node)

        # 定义边
        workflow.add_edge(START, "planner")
        
        # 并行分支：从 Planner 同时流向三个检索节点
        workflow.add_edge("planner", "retrieve_function")
        workflow.add_edge("planner", "retrieve_material")
        workflow.add_edge("planner", "retrieve_site")

        # 汇聚：三个检索节点都流向 Aggregator
        workflow.add_edge("retrieve_function", "aggregator")
        workflow.add_edge("retrieve_material", "aggregator")
        workflow.add_edge("retrieve_site", "aggregator")

        # 评分判断
        workflow.add_edge("aggregator", "grader")
        
        # 条件边：根据分数决定是生成还是重写
        workflow.add_conditional_edges(
            "grader",
            self._check_relevance,
            {
                "pass": "generator",
                "fail": "rewriter"
            }
        )
        
        workflow.add_edge("rewriter", "planner") # 重写后回到规划
        workflow.add_edge("generator", END)

        self.app = workflow.compile()

    # --- 3. 节点具体实现 ---

    def _planner_node(self, state: DesignState):
        """规划节点：将用户需求拆解为三个维度的搜索指令"""
        messages = state["messages"]
        # 获取最新的用户问题（如果是重试，query可能在rewriter中更新了）
        query = state.get("original_query") or messages[-1].content
        
        print(f"\n[Planner] 正在拆解需求: {query}")

        class SearchPlan(BaseModel):
            function_query: str = Field(description="针对核心功能、平面布局、剖面关系的搜索词")
            material_query: str = Field(description="针对材质肌理、立面风格、氛围的搜索词")
            site_query: str = Field(description="针对场地关系、城市界面、入口处理的搜索词")

        prompt = (
            f"你是一位建筑设计搜索专家。请将设计师的需求 '{query}' 拆解为三个独立的搜索维度的英文关键词或短语，"
            "以便在向量数据库中进行跨界搜索。\n"
            "1. Function: 关注功能排布、流线、黑匣子/大剧院等核心类型。\n"
            "2. Material: 关注红砖、木材、混凝土等材质以及光影氛围。\n"
            "3. Site: 关注与城市的连接、入口处理、高差处理等场地文脉。\n"
            "请直接输出 JSON。"
        )

        structured_llm = self.llm.with_structured_output(SearchPlan)
        plan = structured_llm.invoke(prompt)

        return {
            "original_query": query,
            "sub_queries": {
                "function": plan.function_query,
                "material": plan.material_query,
                "site": plan.site_query
            },
            # 清空之前的检索结果，避免累积
            "retrieved_docs": [] 
        }

    def _retrieve_function_node(self, state: DesignState):
        """检索分支 A：功能"""
        query = state["sub_queries"]["function"]
        print(f"[Retrieve A] 功能维度搜索: {query}")
        docs = self.retriever.invoke(query)
        # 简单打标，方便后续追踪（可选）
        for d in docs: 
            d.metadata["source_dim"] = "function"
        return {"retrieved_docs": docs[:3]} # 每个维度取 top 3

    def _retrieve_material_node(self, state: DesignState):
        """检索分支 B：材质"""
        query = state["sub_queries"]["material"]
        print(f"[Retrieve B] 材质维度搜索: {query}")
        docs = self.retriever.invoke(query)
        for d in docs: 
            d.metadata["source_dim"] = "material"
        return {"retrieved_docs": docs[:3]}

    def _retrieve_site_node(self, state: DesignState):
        """检索分支 C：场地"""
        query = state["sub_queries"]["site"]
        print(f"[Retrieve C] 场地维度搜索: {query}")
        docs = self.retriever.invoke(query)
        for d in docs: 
            d.metadata["source_dim"] = "site"
        return {"retrieved_docs": docs[:3]}

    def _aggregator_node(self, state: DesignState):
        """聚合节点：合并结果并去重"""
        all_docs = state["retrieved_docs"]
        unique_docs = []
        seen_contents = set()
        
        # 优先保留不同维度的文档
        for doc in all_docs:
            # 使用 page_content 的前100个字符作为去重指纹
            fingerprint = doc.page_content[:100]
            if fingerprint not in seen_contents:
                seen_contents.add(fingerprint)
                unique_docs.append(doc)
        
        print(f"[Aggregator] 合并后共有 {len(unique_docs)} 个唯一案例")
        
        # 如果数量太多，再次进行 Rerank
        if len(unique_docs) > self.top_k * 2:
             unique_docs = self.reranker.rerank(state["original_query"], unique_docs, top_k=self.top_k)

        return {"unique_docs": unique_docs}

    def _grader_node(self, state: DesignState):
        """评分节点：评估案例集整体质量"""
        query = state["original_query"]
        docs = state["unique_docs"]
        retry_count = state.get("retry_count", 0)

        if not docs:
            return {"relevance_score": 0.0}

        doc_summary = "\n".join([f"- {d.metadata.get('project_name', 'Unknown')}: {d.page_content[:100]}..." for d in docs[:5]])

        class Grade(BaseModel):
            score: float = Field(description="0.0 到 1.0 之间的相关性分数")
            reason: str = Field(description="评分理由")

        prompt = (
            f"用户需求: {query}\n\n"
            f"检索到的案例摘要:\n{doc_summary}\n\n"
            "请评估这些案例是否足以作为设计参考？"
            "我们需要确保案例覆盖了功能、材质或场地中的至少两个维度。"
            "请给出 0.0-1.0 的分数。0.7以上为合格。"
        )

        structured_llm = self.llm.with_structured_output(Grade)
        result = structured_llm.invoke(prompt)

        print(f"[Grader] 评分: {result.score} ({result.reason})")

        # 如果是第一次评分，保存结果
        if retry_count == 0:
            return {
                "relevance_score": result.score,
                "first_attempt_docs": docs.copy(),
                "first_attempt_score": result.score
            }
        else:
            # 如果是重试后的评分，与第一次对比
            first_score = state.get("first_attempt_score", 0.0)
            if result.score < first_score:
                print(f"[Grader] 重写后评分更低 ({result.score} < {first_score})，恢复使用原始查询结果")
                return {
                    "relevance_score": first_score,
                    "unique_docs": state.get("first_attempt_docs", [])
                }
            else:
                return {"relevance_score": result.score}

    def _check_relevance(self, state: DesignState):
        """条件边判断逻辑"""
        retry_count = state.get("retry_count", 0)
        if state["relevance_score"] >= 0.7 or retry_count >= 2:
            return "pass"
        return "fail"

    def _rewriter_node(self, state: DesignState):
        """重写节点：优化查询方向"""
        print("[Rewriter] 检索结果不理想，正在重写查询策略...")
        original_query = state["original_query"]
        
        prompt = f"用户最初的查询是 '{original_query}'，但在之前的检索中没找到足够好的匹配。请尝试换一种更通用或更具描述性的说法，以便更好地进行语义检索。"
        
        response = self.llm.invoke(prompt)
        return {
            "original_query": response.content, # 更新 query
            "retry_count": state.get("retry_count", 0) + 1,
            "retrieved_docs": [] # 清空旧文档
        }

    def _generator_node(self, state: DesignState):
        """生成节点：输出最终 JSON"""
        print("[Generator] 正在生成最终设计简报...")
        query = state.get("original_query")
        docs = state["unique_docs"]
        
        # 格式化文档内容
        context_str = self._format_documents(docs)
        
        prompt = self._get_generate_prompt(query, context_str)
        response = self.llm.invoke(prompt)
        
        return {"messages": [response]}

    # --- 4. 辅助函数保持不变 ---
    def _format_documents(self, docs: List) -> str:
        """
        格式化建筑案例文档供 LLM 参考

        LLM 需要在答案中返回以下 5 个字段：
        - 案例名称（project_name）
        - 设计策略（从 description 或 tags 中提取）
        - 启示（基于案例的总结性内容）
        - 图片链接（images 字段中的 image_url）
        - 案例链接（project_url）
        """
        results = []

        for d in docs:
            # 提取基本信息
            project_name = d.metadata.get('project_name', 'Unknown')
            topic = d.metadata.get('topic', '')
            location = d.metadata.get('location', '')
            year = d.metadata.get('year', '')
            area = d.metadata.get('area', '')
            project_url = d.metadata.get('project_url', '')

            # 提取标签（设计策略）
            tags_str = d.metadata.get('tags', '[]')
            try:
                tags = json.loads(tags_str) if isinstance(tags_str, str) else tags_str
                design_strategy = '、'.join(tags) if tags else '未分类'
            except:
                design_strategy = '未分类'

            # 提取图片链接
            images_str = d.metadata.get('images', '[]')
            try:
                images = json.loads(images_str) if isinstance(images_str, str) else images_str
                image_urls = [img.get('url', '') for img in images if isinstance(img, dict) and img.get('url')]
                image_links = '\n'.join([f"  - {url}" for url in image_urls]) if image_urls else '暂无图片'
            except:
                image_links = '暂无图片'

            # 格式化输出（供 LLM 参考）
            formatted = (
                f"项目名称: {project_name}\n"
                f"建筑类型: {topic}\n"
                f"位置: {location}\n"
                f"年份: {year}\n"
                f"面积: {area}\n"
                f"设计策略: {design_strategy}\n"
                f"图片链接: {image_links}\n"
                f"案例链接: {project_url if project_url else '暂无链接'}\n"
                f"详细内容: {d.page_content}"
            )
            results.append(formatted)

        return "\n\n" + "="*60 + "\n\n".join(results)

    def _get_generate_prompt(self, question: str, context: str) -> str:
        """建筑案例库的生成提示词 - 返回多个案例的 JSON 格式"""
        return (
            "你是一个专业的建筑案例分析专家。基于以下检索到的建筑案例回答用户问题。\n\n"
            f"【重要】请尽可能返回不少于 {self.min_cases} 个相关案例（如果确实没有足够的相关案例可以少于这个数）。\n\n"
            "【输出格式】请以 JSON 格式输出，结构如下：\n"
            "```json\n"
            "{\n"
            '  "query": "用户的原始问题",\n'
            '  "total_cases": 案例数量,\n'
            '  "cases": [\n'
            "    {\n"
            '      "案例名称": "项目名称",\n'
            '      "设计策略": "项目采用的设计策略和特点",\n'
            '      "启示": "从该案例中可以获得的启示和经验",\n'
            '      "图片链接": ["图片URL1", "图片URL2"],\n'
            '      "案例链接": "项目详细链接或来源"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "```\n\n"
            "分析要点：\n"
            "1. 案例的建筑类型和功能\n"
            "2. 设计的创新点和特色\n"
            "3. 地理位置和气候适应性\n"
            "4. 建筑面积和规模\n"
            "5. 可以借鉴的设计经验\n\n"
            "回答要求：\n"
            "- 专业、准确，引用具体案例信息\n"
            f"- 尽可能返回不少于 {self.min_cases} 个相关案例\n"
            "- 只返回与问题相关的案例，不相关的案例不要包含\n"
            "- 如果在上下文中找不到相关案例，返回空的 cases 数组\n"
            "- 不要编造或推测没有依据的信息\n"
            "- 必须严格按照 JSON 格式输出\n\n"
            f"问题: {question}\n\n"
            f"参考案例: {context}"
        )

    def _get_grade_prompt(self, question: str, context: str) -> str:
        """案例库的评分提示词"""
        return (
            "你是一个建筑设计案例评估专家。\n"
            "请评估以下检索到的建筑案例是否与用户的设计需求相关。\n\n"
            f"用户需求: {question}\n\n"
            f"检索到的案例:\n{context}\n\n"
            "评估标准：\n"
            "- 案例是否涵盖了用户需求的功能、材质或场地维度\n"
            "- 案例的设计特点是否能为用户提供参考价值\n"
            "- 案例的规模和类型是否与用户需求相符\n\n"
            "如果案例包含与需求相关的设计启示，请评分为 'yes'，否则为 'no'。"
        )

    def _get_rewrite_prompt(self, question: str) -> str:
        """案例库的重写提示词"""
        return (
            "用户提出了一个建筑设计需求，但之前的案例检索未能找到足够相关的参考。\n"
            "请推断用户的设计意图，并重写需求描述，使其更容易在建筑案例库中被检索到。\n\n"
            "重写建议：\n"
            "- 考虑用户可能关心的建筑类型（办公、住宅、商业等）\n"
            "- 考虑设计的关键特征（开放式、模块化、可持续等）\n"
            "- 考虑材质、光影、流线等设计要素\n"
            "- 考虑与场地、城市的关系\n\n"
            f"原始需求: {question}\n"
            "请只输出重写后的需求描述。"
        )

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

            # 初始化 state，包含新增的字段
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "original_query": user_input,
                "sub_queries": {},
                "retrieved_docs": [],
                "unique_docs": [],
                "relevance_score": 0.0,
                "retry_count": 0,
                "first_attempt_docs": [],
                "first_attempt_score": 0.0
            }

            try:
                for chunk in self.app.stream(initial_state):
                    pass

                final_state = chunk
                last_node = list(final_state.keys())[0]
                last_msg = final_state[last_node]["messages"][-1]
                print(f"\nAssistant: {last_msg.content}")

            except Exception as e:
                print(f"\n[Error] 执行出错: {e}")


