"""
文件索引模块
- 扫描 output_pages 目录
- 建立规范编号到文件的映射
- 提供文件查找功能
"""

import os
import re
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass
from pathlib import Path

from spec_locator.config import PathConfig

logger = logging.getLogger(__name__)


@dataclass
class SpecFile:
    """规范文件信息"""
    spec_code: str  # 规范编号（如 23J909）
    page_code: str  # 页码（如 1-11, C11）
    file_path: str  # 文件路径
    file_name: str  # 文件名
    directory: str  # 所在目录名


class FileIndex:
    """文件索引"""

    def __init__(self, data_dir: str = None):
        """
        初始化文件索引

        Args:
            data_dir: 数据目录路径，默认使用配置中的 SPEC_DATA_DIR
        """
        if data_dir is None:
            data_dir = PathConfig.SPEC_DATA_DIR
        
        self.data_dir = Path(data_dir)
        self.index: Dict[str, List[SpecFile]] = {}
        self._build_index()

    def _build_index(self):
        """构建文件索引"""
        if not self.data_dir.exists():
            logger.warning(f"Data directory not found: {self.data_dir}")
            return

        logger.info(f"Building file index from: {self.data_dir}")
        file_count = 0

        # 遍历所有目录
        for dir_path in self.data_dir.iterdir():
            if not dir_path.is_dir():
                continue

            # 从目录名提取规范编号
            spec_code = self._extract_spec_from_dirname(dir_path.name)
            if not spec_code:
                logger.debug(f"Could not extract spec code from directory: {dir_path.name}")
                continue

            # 扫描目录中的PDF文件
            pdf_files = list(dir_path.glob("*.pdf"))
            logger.debug(f"Found {len(pdf_files)} PDF files in {dir_path.name}")

            for pdf_file in pdf_files:
                page_code = self._extract_page_from_filename(pdf_file.name)
                if page_code:
                    spec_file = SpecFile(
                        spec_code=spec_code,
                        page_code=page_code,
                        file_path=str(pdf_file),
                        file_name=pdf_file.name,
                        directory=dir_path.name,
                    )

                    # 添加到索引
                    if spec_code not in self.index:
                        self.index[spec_code] = []
                    self.index[spec_code].append(spec_file)
                    file_count += 1

        logger.info(f"Index built: {len(self.index)} spec codes, {file_count} files")

    def _extract_spec_from_dirname(self, dirname: str) -> Optional[str]:
        """
        从目录名提取规范编号

        Examples:
            "23J909 工程做法（高清）" -> "23J909"
            "已识别_06J908-1 公共建筑节能构造" -> "06J908-1"
            "20G908-1_建筑工程施工质量常见问题" -> "20G908-1"

        Args:
            dirname: 目录名

        Returns:
            规范编号或 None
        """
        # 去除"已识别_"前缀
        dirname = re.sub(r'^已识别_', '', dirname)

        # 匹配规范编号模式：数字+字母+数字，可能带短横线
        match = re.search(r'(\d{2,3}[A-Z]+\d{1,4}(?:-\d+)?)', dirname, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        return None

    def _extract_page_from_filename(self, filename: str) -> Optional[str]:
        """
        从文件名提取页码

        Examples:
            "23J909_1-11.pdf" -> "1-11"
            "23J909_C11.pdf" -> "C11"
            "06J908-1_A5.pdf" -> "A5"

        Args:
            filename: 文件名

        Returns:
            页码或 None
        """
        # 去除.pdf后缀
        name = filename.replace('.pdf', '')

        # 尝试多种模式
        patterns = [
            r'_([A-Z]\d+(?:-\d+)?)',  # _C11, _C11-2
            r'_(\d+-\d+)',             # _1-11
            r'_([A-Z]+\d+)',           # _ABC123
            r'_(\d+)',                 # _11
        ]

        for pattern in patterns:
            match = re.search(pattern, name)
            if match:
                return match.group(1)

        return None

    def find_file(self, spec_code: str, page_code: str) -> Optional[SpecFile]:
        """
        查找指定规范和页码的文件

        Args:
            spec_code: 规范编号（如 12J2）
            page_code: 页码（如 C11）

        Returns:
            匹配的文件信息或 None
        """
        # 标准化规范编号
        spec_code = spec_code.upper()

        # 查找完全匹配
        if spec_code in self.index:
            for spec_file in self.index[spec_code]:
                if self._page_match(spec_file.page_code, page_code):
                    logger.info(f"Found exact match: {spec_file.file_name}")
                    return spec_file

        # 尝试模糊匹配（部分规范编号匹配）
        for indexed_code in self.index.keys():
            if spec_code in indexed_code or indexed_code in spec_code:
                for spec_file in self.index[indexed_code]:
                    if self._page_match(spec_file.page_code, page_code):
                        logger.info(f"Found fuzzy match: {spec_file.file_name}")
                        return spec_file

        logger.warning(f"No file found for {spec_code} page {page_code}")
        return None

    def _page_match(self, indexed_page: str, query_page: str) -> bool:
        """
        判断页码是否匹配

        Args:
            indexed_page: 索引中的页码
            query_page: 查询的页码

        Returns:
            是否匹配
        """
        # 完全匹配
        if indexed_page.upper() == query_page.upper():
            return True

        # 去掉前导零后匹配
        indexed_normalized = indexed_page.lstrip('0').upper()
        query_normalized = query_page.lstrip('0').upper()
        if indexed_normalized == query_normalized:
            return True

        return False

    def get_all_specs(self) -> List[str]:
        """获取所有规范编号"""
        return list(self.index.keys())

    def get_spec_files(self, spec_code: str) -> List[SpecFile]:
        """
        获取指定规范的所有文件

        Args:
            spec_code: 规范编号

        Returns:
            文件列表
        """
        spec_code = spec_code.upper()
        return self.index.get(spec_code, [])

    def get_stats(self) -> Dict[str, int]:
        """获取索引统计信息"""
        total_files = sum(len(files) for files in self.index.values())
        return {
            "spec_codes": len(self.index),
            "total_files": total_files,
        }
