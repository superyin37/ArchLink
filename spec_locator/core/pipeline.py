"""
核心处理流水线
- 串联所有子模块
- 控制整体识别流程
- 对异常情况进行统一处理
"""

import logging
import numpy as np
from typing import List, Optional, Dict, Any

from spec_locator.config import ErrorCode, ERROR_MESSAGES
from spec_locator.preprocess import ImagePreprocessor
from spec_locator.ocr import OCREngine
from spec_locator.parser import SpecCodeParser, PageCodeParser
from spec_locator.postprocess import ConfidenceEvaluator, ResultFilter, SpecMatch
from spec_locator.database import FileIndex

logger = logging.getLogger(__name__)


class SpecLocatorPipeline:
    """规范定位流水线"""

    def __init__(
        self,
        use_gpu: bool = False,
        ocr_threshold: float = 0.3,
        max_distance: int = 100,
        data_dir: str = None,
    ):
        """
        初始化流水线

        Args:
            use_gpu: 是否使用 GPU
            ocr_threshold: OCR 置信度阈值
            max_distance: 最大邻近距离
            data_dir: 数据目录路径
        """
        self.preprocessor = ImagePreprocessor()
        self.ocr_engine = OCREngine(use_gpu=use_gpu, conf_threshold=ocr_threshold)
        self.spec_parser = SpecCodeParser()
        self.page_parser = PageCodeParser(max_distance=max_distance)
        self.confidence_evaluator = ConfidenceEvaluator()
        self.file_index = FileIndex(data_dir=data_dir)

    def process(self, image: np.ndarray) -> Dict[str, Any]:
        """
        处理图像并返回识别结果

        Args:
            image: 输入图像（BGR 格式）

        Returns:
            包含结果或错误的字典
        """
        try:
            # 1. 图像预处理
            logger.debug("Starting preprocessing...")
            processed_image = self.preprocessor.preprocess(image)

            # 2. OCR 识别
            logger.debug("Starting OCR...")
            text_boxes = self.ocr_engine.recognize(image)  # 使用原图而非处理后的图

            if not text_boxes:
                return self._error_response(ErrorCode.NO_TEXT)

            # 3. 规范编号识别
            logger.debug("Parsing spec codes...")
            spec_codes = self.spec_parser.parse(text_boxes)

            if not spec_codes:
                return self._error_response(ErrorCode.NO_SPEC_CODE)

            # 4. 页码识别
            logger.debug("Parsing page codes...")
            page_codes = self.page_parser.parse(text_boxes)

            if not page_codes:
                return self._error_response(ErrorCode.NO_PAGE_CODE)

            # 5. 置信度评估与结果排序
            logger.debug("Evaluating confidence...")
            matches = self.confidence_evaluator.evaluate(spec_codes, page_codes)

            if not matches:
                return self._error_response(ErrorCode.NO_MATCH)

            # 6. 生成返回结果
            return self._success_response(matches)

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            return self._error_response(ErrorCode.INTERNAL_ERROR)

    def _success_response(self, matches: List[SpecMatch]) -> Dict[str, Any]:
        """生成成功响应"""
        best_match = matches[0]
        candidates = ResultFilter.get_top_n(matches, n=5)

        # 查找对应的PDF文件
        pdf_file = self.file_index.find_file(best_match.spec_code, best_match.page_code)

        response = {
            "success": True,
            "spec": {
                "code": best_match.spec_code,
                "page": best_match.page_code,
                "confidence": round(best_match.confidence, 4),
            },
            "candidates": [
                {
                    "code": match.spec_code,
                    "page": match.page_code,
                    "confidence": round(match.confidence, 4),
                }
                for match in candidates
            ],
        }

        # 如果找到PDF文件，添加文件信息和下载URL
        if pdf_file:
            download_url = f"/api/download/{best_match.spec_code}/{best_match.page_code}"
            response["file"] = {
                "path": pdf_file.file_path,
                "name": pdf_file.file_name,
                "directory": pdf_file.directory,
                "download_url": download_url,
            }
            logger.info(f"Found PDF file: {pdf_file.file_name}, download URL: {download_url}")
        else:
            response["file"] = None
            logger.warning(f"PDF file not found for {best_match.spec_code} page {best_match.page_code}")

        return response

    def _error_response(self, error_code: ErrorCode) -> Dict[str, Any]:
        """生成错误响应"""
        return {
            "success": False,
            "error_code": error_code.value,
            "message": ERROR_MESSAGES.get(error_code, "Unknown error"),
        }
