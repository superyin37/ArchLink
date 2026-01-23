"""
数据加载器实现
"""
import os
import json
import sqlite3
from typing import Generator, List, Dict, Any
import pandas as pd

from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_core.documents import Document

from base import DataLoader


class ExcelCaseLoader(DataLoader):
    """从 Excel 文件加载案例数据"""

    def __init__(self, excel_path: str, chunk_size: int = 600, chunk_overlap: int = 100):
        """
        初始化 Excel 案例加载器

        Args:
            excel_path: Excel 文件路径
            chunk_size: 文本分割块大小
            chunk_overlap: 文本分割块重叠大小
        """
        self.excel_path = excel_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def load(self) -> Generator[Document, None, None]:
        """
        从 Excel 文件读取案例数据并生成文档流

        Yields:
            Document: 分割后的文档块
        """
        try:
            df = pd.read_excel(self.excel_path)
        except Exception as e:
            print(f"[Error] 无法读取 Excel 文件: {e}")
            return

        for idx, row in df.iterrows():
            # 构建文档内容：合并案例赏析和原文
            content_parts = []
            if pd.notna(row.get('案例赏析')):
                content_parts.append(str(row['案例赏析']))
            if pd.notna(row.get('原文')):
                content_parts.append(str(row['原文']))

            if not content_parts:
                continue

            page_content = "\n\n".join(content_parts)

            # 构建元数据
            metadata = {
                "source": self.excel_path,
                "doc_name": "案例库",
                "case_id": str(row.get('序号', idx)),
                "case_name": str(row.get('案例名称', ''))
            }

            if pd.notna(row.get('链接')):
                metadata["url"] = str(row['链接'])

            # 创建文档并分割
            doc = Document(page_content=page_content, metadata=metadata)
            chunks = self.text_splitter.split_documents([doc])

            for chunk in chunks:
                yield chunk


class GuiFanLoader(DataLoader):
    """从规范库文件夹加载规范数据（Markdown 格式）"""

    def __init__(self, root_dir: str, chunk_size: int = 600, chunk_overlap: int = 100):
        """
        初始化规范加载器

        Args:
            root_dir: 规范库根目录路径
            chunk_size: 文本分割块大小
            chunk_overlap: 文本分割块重叠大小
        """
        self.root_dir = root_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3"), ("####", "Header 4")]
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def load(self) -> Generator[Document, None, None]:
        """
        从规范库文件夹读取 Markdown 文件并生成文档流
        遵循 load_splits.py 的内部生成器模式

        Yields:
            Document: 分割后的文档块
        """
        # 内部生成器：读取文件
        def _file_generator():
            if not os.path.exists(self.root_dir):
                return

            for folder_name in os.listdir(self.root_dir):
                folder_path = os.path.join(self.root_dir, folder_name)
                if not os.path.isdir(folder_path):
                    continue

                # 查找 Markdown 文件
                md_file_path = os.path.join(folder_path, f"{folder_name}.md")
                if not os.path.exists(md_file_path):
                    md_files = [f for f in os.listdir(folder_path) if f.endswith(".md")]
                    if md_files:
                        md_file_path = os.path.join(folder_path, md_files[0])
                    else:
                        continue

                # 读取 Markdown 文件（使用 UTF-8 + errors='ignore' 处理特殊字节）
                try:
                    with open(md_file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    if not content.strip():
                        continue
                except Exception:
                    continue

                # 构建基础元数据
                base_name = os.path.splitext(os.path.basename(md_file_path))[0]
                metadata = {
                    "source": os.path.abspath(md_file_path),
                    "doc_name": folder_name
                }

                # 尝试加载 meta.json 文件
                meta_file_path = os.path.join(folder_path, f"{base_name}_meta.json")
                if os.path.exists(meta_file_path):
                    try:
                        with open(meta_file_path, "r", encoding="utf-8") as f:
                            json_meta = json.load(f)
                            for k, v in json_meta.items():
                                if isinstance(v, (list, dict)):
                                    metadata[k] = json.dumps(v, ensure_ascii=False)
                                else:
                                    metadata[k] = v
                    except:
                        pass

                yield Document(page_content=content, metadata=metadata)

        # 内部逻辑：切分（遵循 load_splits.py 的模式）
        docs_stream = _file_generator()

        for doc in docs_stream:
            try:
                header_splits = self.markdown_splitter.split_text(doc.page_content)
                for split in header_splits:
                    split.metadata.update(doc.metadata)
            except Exception:
                header_splits = [doc]

            final_chunks = self.text_splitter.split_documents(header_splits)
            for chunk in final_chunks:
                yield chunk


class AnliKuLoader(DataLoader):
    """从 ANLIKU 数据库加载建筑案例数据"""

    def __init__(self, anliku_root_dir: str, chunk_size: int = 600, chunk_overlap: int = 100):
        """
        初始化 ANLIKU 加载器

        Args:
            anliku_root_dir: ANLIKU 根目录路径
            chunk_size: 文本分割块大小
            chunk_overlap: 文本分割块重叠大小
        """
        self.anliku_root_dir = anliku_root_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "，", " ", ""]
        )

    def _extract_project_data(self, db_path: str, topic: str) -> Generator[Dict[str, Any], None, None]:
        """从数据库提取项目数据"""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM main.projects")
            projects = cursor.fetchall()

            for project in projects:
                project_id = project['project_id']
                project_data = {
                    'project_id': project_id,
                    'project_name': project['project_name'],
                    'location': project['location'],
                    'year': project['year'],
                    'area': project['area'],
                    'description': project['description'],
                    'project_url': project['project_url'],
                    'topic': topic,
                    'tags': [],
                    'images': []
                }

                cursor.execute("SELECT tag FROM main.project_tags WHERE project_id = ?", (project_id,))
                tags = cursor.fetchall()
                project_data['tags'] = [tag['tag'] for tag in tags]

                cursor.execute("SELECT image_url, local_path FROM main.project_images WHERE project_id = ? ORDER BY image_index", (project_id,))
                images = cursor.fetchall()
                project_data['images'] = [
                    {'url': img['image_url'], 'local_path': img['local_path']}
                    for img in images
                ]

                yield project_data

            conn.close()
        except Exception as e:
            print(f"[Error] Failed to extract data from {db_path}: {e}")

    def load(self) -> Generator[Document, None, None]:
        """加载 ANLIKU 数据并返回文档流"""
        for topic_dir in os.listdir(self.anliku_root_dir):
            topic_path = os.path.join(self.anliku_root_dir, topic_dir)
            if not os.path.isdir(topic_path):
                continue

            for subdir in os.listdir(topic_path):
                subdir_path = os.path.join(topic_path, subdir)
                if not os.path.isdir(subdir_path):
                    continue

                db_path = os.path.join(subdir_path, "architecture_projects.db")
                if not os.path.exists(db_path):
                    continue

                for project_data in self._extract_project_data(db_path, topic_dir):
                    content_parts = [
                        f"项目名称: {project_data['project_name']}",
                        f"建筑类型: {project_data['topic']}",
                    ]

                    if project_data['location']:
                        content_parts.append(f"位置: {project_data['location']}")
                    if project_data['year']:
                        content_parts.append(f"年份: {project_data['year']}")
                    if project_data['area']:
                        content_parts.append(f"面积: {project_data['area']}")
                    if project_data['description']:
                        content_parts.append(f"描述: {project_data['description']}")
                    if project_data['tags']:
                        content_parts.append(f"标签: {', '.join(project_data['tags'])}")

                    content = "\n".join(content_parts)

                    metadata = {
                        'project_id': project_data['project_id'],
                        'project_name': project_data['project_name'],
                        'topic': project_data['topic'],
                        'tags': json.dumps(project_data['tags'], ensure_ascii=False),
                        'images': json.dumps(project_data['images'], ensure_ascii=False),
                        'project_url': project_data['project_url'] or '',
                        'location': project_data['location'] or '',
                        'year': project_data['year'] or '',
                        'area': project_data['area'] or ''
                    }

                    chunks = self.text_splitter.split_text(content)
                    for i, chunk in enumerate(chunks):
                        chunk_metadata = metadata.copy()
                        chunk_metadata['chunk_index'] = i
                        yield Document(page_content=chunk, metadata=chunk_metadata)

