"""
建筑工程领域的 RAG 执行器实现
"""
from typing import List
from executor import RAGExecutor


class ConstructionRAGExecutor(RAGExecutor):
    """建筑工程 RAG 系统执行器"""

    def _format_documents(self, docs: List) -> str:
        """格式化建筑工程文档"""
        results = []
        for d in docs:
            source = d.metadata.get('doc_name', 'Unknown')
            h1 = d.metadata.get('Header 1', '')
            h2 = d.metadata.get('Header 2', '')
            results.append(f"【来源: {source} | {h1} > {h2}】\n{d.page_content}")
        return "\n\n".join(results)

    def _get_grade_prompt(self, question: str, context: str) -> str:
        """建筑工程领域的评分提示词"""
        return (
            "你是一个建筑工程文档评估专家。\n"
            "请评估以下检索到的文档是否与用户问题相关。\n\n"
            f"用户问题: {question}\n\n"
            f"检索文档: {context}\n\n"
            "如果文档包含与问题相关的关键词或语义，请评分为 'yes'，否则为 'no'。"
        )

    def _get_rewrite_prompt(self, question: str) -> str:
        """建筑工程领域的重写提示词"""
        return (
            "用户问了一个关于建筑工程的问题，但之前的检索未能找到相关信息。\n"
            "请推断用户的潜在意图，并重写问题，使其更容易在建筑规范或教材中被检索到。\n"
            f"原始问题: {question}\n"
            "请只输出重写后的问题。"
        )

    def _get_generate_prompt(self, question: str, context: str) -> str:
        """建筑工程领域的生成提示词"""
        return (
            "你是一个专业的建筑工程助手。基于以下检索到的规范和教材内容回答用户问题。\n"
            "如果在上下文中找不到答案，请诚实地说不知道，不要编造。\n"
            "回答应专业、准确，并尽量引用具体的规范章节。\n\n"
            f"问题: {question}\n\n"
            f"参考内容: {context}"
        )


class AnliKuRAGExecutor(RAGExecutor):
    """建筑案例库 RAG 系统执行器"""

    def _format_documents(self, docs: List) -> str:
        """格式化建筑案例文档"""
        results = []
        for d in docs:
            project_name = d.metadata.get('project_name', 'Unknown')
            topic = d.metadata.get('topic', '')
            location = d.metadata.get('location', '')
            year = d.metadata.get('year', '')
            results.append(
                f"【项目: {project_name} | 类型: {topic} | 位置: {location} | 年份: {year}】\n"
                f"{d.page_content}"
            )
        return "\n\n".join(results)

    def _get_grade_prompt(self, question: str, context: str) -> str:
        """建筑案例库的评分提示词"""
        return (
            "你是一个建筑案例评估专家。\n"
            "请评估以下检索到的建筑案例是否与用户问题相关。\n\n"
            f"用户问题: {question}\n\n"
            f"检索案例: {context}\n\n"
            "如果案例包含与问题相关的建筑类型、设计特点或其他相关信息，请评分为 'yes'，否则为 'no'。"
        )

    def _get_rewrite_prompt(self, question: str) -> str:
        """建筑案例库的重写提示词"""
        return (
            "用户问了一个关于建筑案例的问题，但之前的检索未能找到相关案例。\n"
            "请推断用户的潜在意图，并重写问题，使其更容易在建筑案例库中被检索到。\n"
            "可以考虑建筑类型、功能、地理位置、设计风格等方面。\n"
            f"原始问题: {question}\n"
            "请只输出重写后的问题。"
        )

    def _get_generate_prompt(self, question: str, context: str) -> str:
        """建筑案例库的生成提示词"""
        return (
            "你是一个建筑案例分析专家。基于以下检索到的建筑案例回答用户问题。\n"
            "请分析案例的设计特点、建筑类型、地理位置等信息。\n"
            "如果在上下文中找不到答案，请诚实地说不知道，不要编造。\n\n"
            f"问题: {question}\n\n"
            f"参考案例: {context}"
        )

