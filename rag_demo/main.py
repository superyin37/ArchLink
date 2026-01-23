import os
from typing import Literal

# LangChain Imports
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
# LangGraph Imports
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

# 导入我们在 load_splits.py 中定义的 Embedding 类
from load_splits import DoubaoVisionEmbeddings

from dotenv import load_dotenv

load_dotenv()
# ==========================================
# 1. 初始化资源 (LLM & VectorStore)
# ==========================================

# 加载现有的向量库
persist_dir = "./chroma_db_doubaotest"
if not os.path.exists(persist_dir):
    print(f"错误: 向量库目录 {persist_dir} 不存在。请先运行 'python load_splits.py' 构建索引。")
    exit(1)

print(">>> 正在加载本地向量库...")
doubao_emb = DoubaoVisionEmbeddings()
vectorstore = Chroma(
    collection_name="construction_doubao_text",
    embedding_function=doubao_emb,
    persist_directory=persist_dir
)
retriever = vectorstore.as_retriever()

# 初始化 LLM
llm = ChatOpenAI(
    model="doubao-seed-1-6-251015", # 请确保这是正确的 Endpoint ID
    api_key=os.environ.get("ARK_API_KEY"),
    base_url=os.environ.get("SEED_API_BASE"),
    temperature=0.1,
    model_kwargs={
        # 频率惩罚 (0.0 ~ 2.0)：数值越大，越禁止模型逐字重复之前的文本
        "frequency_penalty": 0.5, 
        # 存在惩罚 (0.0 ~ 2.0)：数值越大，越禁止模型谈论已经谈论过的话题
        "presence_penalty": 0.3,
        # 显式停止词：告诉模型遇到这些词就强制闭嘴
        # 豆包有时候不会自动输出标准的 <EOS>，我们手动帮它刹车
        "stop": ["<|endoftext|>", "User:", "\nUser:", "Question:"]
    }
)

# ==========================================
# 2. 定义 Tool 和 Node 逻辑
# ==========================================

@tool
def retrieve_construction_specs(query: str):
    """Search construction manuals."""
    docs = retriever.invoke(query) 
    results = []
    for d in docs:
        source = d.metadata.get('doc_name', 'Unknown')
        h1 = d.metadata.get('Header 1', '')
        h2 = d.metadata.get('Header 2', '')
        results.append(f"【来源: {source} | {h1} > {h2}】\n{d.page_content}")
    return "\n\n".join(results)

tools = [retrieve_construction_specs]

def generate_query_or_respond(state: MessagesState):
    """LLM 决定是直接回答用户，还是调用工具去检索。"""
    llm_with_tools = llm.bind_tools(tools)
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

class GradeDocuments(BaseModel):
    binary_score: str = Field(description="Relevance score: 'yes' if relevant, or 'no' if not relevant")

def grade_documents(state: MessagesState) -> Literal["generate_answer", "rewrite_question"]:
    """评估检索到的文档是否与问题相关。"""
    messages = state["messages"]
    last_message = messages[-1]
    question = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    context = last_message.content

    GRADE_PROMPT = (
        "You are a grader assessing relevance of a retrieved document to a user question. \n"
        "Here is the retrieved document: \n\n {context} \n\n"
        "Here is the user question: {question} \n"
        "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n"
        "Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."
    )

    prompt = GRADE_PROMPT.format(question=question, context=context)
    structured_llm = llm.with_structured_output(GradeDocuments)
    response = structured_llm.invoke(prompt)
    
    if response.binary_score == "yes":
        return "generate_answer"
    else:
        return "rewrite_question"

def rewrite_question(state: MessagesState):
    """如果检索结果不相关，重写问题。"""
    messages = state["messages"]
    question = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    
    REWRITE_PROMPT = (
        "用户问了一个关于建筑工程的问题，但之前的检索未能找到相关信息。\n"
        "请推断用户的潜在意图，并重写问题，使其更容易在建筑规范或教材中被检索到。\n"
        "原始问题: {question}\n"
        "请只输出重写后的问题。"
    )
    
    response = llm.invoke(REWRITE_PROMPT.format(question=question))
    return {"messages": [HumanMessage(content=response.content)]}

def generate_answer(state: MessagesState):
    """根据上下文生成最终答案。"""
    messages = state["messages"]
    question = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    context = next((m.content for m in reversed(messages) if m.type == 'tool'), "")

    GENERATE_PROMPT = (
        "你是一个专业的建筑工程助手。基于以下检索到的规范和教材内容回答用户问题。\n"
        "如果在上下文中找不到答案，请诚实地说不知道，不要编造。\n"
        "回答应专业、准确，并尽量引用具体的规范章节。\n\n"
        "问题: {question} \n"
        "参考内容: {context}"
    )
    
    response = llm.invoke(GENERATE_PROMPT.format(question=question, context=context))
    return {"messages": [response]}

# ==========================================
# 3. 构建 LangGraph
# ==========================================

workflow = StateGraph(MessagesState)
workflow.add_node("generate_query_or_respond", generate_query_or_respond)
workflow.add_node("retrieve", ToolNode(tools))
workflow.add_node("rewrite_question", rewrite_question)
workflow.add_node("generate_answer", generate_answer)

workflow.add_edge(START, "generate_query_or_respond")
workflow.add_conditional_edges(
    "generate_query_or_respond",
    tools_condition,
    {"tools": "retrieve", END: END},
)
workflow.add_conditional_edges("retrieve", grade_documents)
workflow.add_edge("generate_answer", END)
workflow.add_edge("rewrite_question", "generate_query_or_respond")

app = workflow.compile()

# ==========================================
# 4. Main Loop
# ==========================================

def main():
    print(f"\n>>> 建筑工程智能助手 (Model: {llm.model_name})")
    print(">>> 请输入问题 (输入 'q' 退出):")
    
    while True:
        try:
            user_input = input("\nUser: ")
        except EOFError:
            break
            
        if user_input.lower() in ["q", "quit", "exit"]:
            break
            
        initial_state = {"messages": [HumanMessage(content=user_input)]}
        
        final_state = None
        # 使用同步流 (如果想用流式 Token 打印，参考之前 turn 的 asyncio 方案)
        try:
            for chunk in app.stream(initial_state):
                final_state = chunk
                # 可以在这里打印中间步骤，例如：
                for node, update in chunk.items():
                   print(f"--- Step: {node} ---")
            
            if final_state:
                # 获取最后一个节点的输出
                last_node = list(final_state.keys())[0]
                last_msg = final_state[last_node]["messages"][-1]
                print(f"\nAssistant: {last_msg.content}")
                
        except Exception as e:
            print(f"\n[Error] 执行出错: {e}")

if __name__ == "__main__":
    main()