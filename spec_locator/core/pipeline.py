"""
核心处理流水线
- 串联所有子模块
- 控制整体识别流程
- 对异常情况进行统一处理
"""

import logging
import numpy as np
from typing import List, Optional, Dict, Any

from spec_locator.config import ErrorCode, ERROR_MESSAGES, PathConfig, LLMConfig
from spec_locator.preprocess import ImagePreprocessor
from spec_locator.ocr import OCREngine
from spec_locator.parser import SpecCodeParser, PageCodeParser
from spec_locator.postprocess import ConfidenceEvaluator, ResultFilter, SpecMatch
from spec_locator.database import FileIndex

logger = logging.getLogger(__name__)


class SpecLocatorPipeline:
    """规范定位流水线（支持多种识别方式）"""

    def __init__(
        self,
        use_gpu: bool = False,
        ocr_threshold: float = 0.3,
        max_distance: int = 300,
        data_dir: str = None,
        lazy_ocr: bool = True,
        recognition_method: str = "ocr",  # 新增参数：识别方式
        llm_api_key: str = None,          # 新增参数：大模型API密钥
    ):
        """
        初始化流水线

        Args:
            use_gpu: 是否使用 GPU
            ocr_threshold: OCR 置信度阈值
            max_distance: 最大邻近距离
            data_dir: 数据目录路径，默认使用配置中的 SPEC_DATA_DIR
            lazy_ocr: 是否使用懒加载OCR（默认True）
            recognition_method: 识别方式 ("ocr" | "llm" | "auto")
            llm_api_key: 大模型API密钥
        """
        self.preprocessor = ImagePreprocessor()
        self.ocr_engine = OCREngine(use_gpu=use_gpu, conf_threshold=ocr_threshold, lazy_load=lazy_ocr)
        self.spec_parser = SpecCodeParser()
        self.page_parser = PageCodeParser(max_distance=max_distance)
        self.confidence_evaluator = ConfidenceEvaluator()
        if data_dir is None:
            data_dir = PathConfig.SPEC_DATA_DIR
        self.file_index = FileIndex(data_dir=data_dir)
        
        # 新增：识别方式配置
        self.recognition_method = recognition_method
        
        # 新增：初始化LLM引擎（如果需要）
        self.llm_engine = None
        if recognition_method in ["llm", "auto"] and LLMConfig.ENABLED:
            try:
                # 根据配置的提供商动态选择引擎
                provider = LLMConfig.PROVIDER
                if provider == "openai":
                    from spec_locator.llm import ChatGPTEngine
                    self.llm_engine = ChatGPTEngine(
                        api_key=llm_api_key or LLMConfig.API_KEY,
                        model=LLMConfig.MODEL,
                        timeout=LLMConfig.TIMEOUT,
                        max_retries=LLMConfig.MAX_RETRIES,
                        prompt_version=LLMConfig.PROMPT_VERSION
                    )
                    logger.info(f"✓ ChatGPT Engine initialized (method={recognition_method})")
                elif provider == "gemini":
                    from spec_locator.llm import GeminiEngine
                    self.llm_engine = GeminiEngine(
                        api_key=llm_api_key or LLMConfig.API_KEY,
                        model=LLMConfig.MODEL,
                        timeout=LLMConfig.TIMEOUT,
                        max_retries=LLMConfig.MAX_RETRIES,
                        prompt_version=LLMConfig.PROMPT_VERSION
                    )
                    logger.info(f"✓ Gemini Engine initialized (method={recognition_method})")
                else:  # doubao (default)
                    from spec_locator.llm import DoubaoEngine
                    self.llm_engine = DoubaoEngine(
                        api_key=llm_api_key or LLMConfig.API_KEY,
                        model=LLMConfig.MODEL,
                        timeout=LLMConfig.TIMEOUT,
                        max_retries=LLMConfig.MAX_RETRIES,
                        prompt_version=LLMConfig.PROMPT_VERSION
                    )
                    logger.info(f"✓ Doubao Engine initialized (method={recognition_method})")
            except Exception as e:
                logger.error(f"Failed to initialize LLM engine ({LLMConfig.PROVIDER}): {e}")
                if recognition_method == "llm":
                    raise  # llm模式必须成功初始化
    
    def warmup(self):
        """预热流水线：加载OCR模型"""
        logger.info("Pipeline 预热中...")
        self.ocr_engine.warmup()
        logger.info("✓ Pipeline 预热完成")

    def process(self, image: np.ndarray) -> Dict[str, Any]:
        """
        处理图像并返回识别结果（支持多种识别方式）

        Args:
            image: 输入图像（BGR 格式）

        Returns:
            包含结果或错误的字典
        """
        # 根据识别方式路由
        if self.recognition_method == "llm":
            return self._process_with_llm(image)
        elif self.recognition_method == "auto":
            return self._process_hybrid(image)
        else:  # "ocr" 或默认
            return self._process_with_ocr(image)

    def _process_with_ocr(self, image: np.ndarray) -> Dict[str, Any]:
        """OCR识别流程（原process方法逻辑）"""
        try:
            # 1. 图像预处理
            logger.debug("Starting preprocessing...")
            processed_image = self.preprocessor.preprocess(image)

            # 2. OCR 识别
            logger.debug("Starting OCR...")
            text_boxes = self.ocr_engine.recognize(image)  # 使用原图而非处理后的图

            if not text_boxes:
                return self._error_response(ErrorCode.NO_TEXT, ocr_texts=[])

            # 3. 规范编号识别
            logger.debug("Parsing spec codes...")
            spec_codes = self.spec_parser.parse(text_boxes)

            # 提取OCR识别到的所有文本（用于错误提示）
            ocr_texts = [box.text for box in text_boxes]

            if not spec_codes:
                return self._error_response(
                    ErrorCode.NO_SPEC_CODE, 
                    ocr_texts=ocr_texts,
                    page_codes=[]
                )

            # 4. 页码识别
            logger.debug("Parsing page codes...")
            page_codes = self.page_parser.parse(text_boxes)

            if not page_codes:
                return self._error_response(
                    ErrorCode.NO_PAGE_CODE,
                    ocr_texts=ocr_texts,
                    spec_codes=[s.code for s in spec_codes]
                )

            # 5. 置信度评估与结果排序
            logger.debug("Evaluating confidence...")
            matches = self.confidence_evaluator.evaluate(spec_codes, page_codes)

            if not matches:
                return self._error_response(
                    ErrorCode.NO_MATCH,
                    ocr_texts=ocr_texts,
                    spec_codes=[s.code for s in spec_codes],
                    page_codes=[p.page for p in page_codes]
                )

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
            response["file_found"] = True
            logger.info(f"Found PDF file: {pdf_file.file_name}, download URL: {download_url}")
        else:
            response["file"] = None
            response["file_found"] = False
            response["warning"] = f"识别成功：{best_match.spec_code} {best_match.page_code}，但数据库中未找到对应文件"
            logger.warning(f"PDF file not found for {best_match.spec_code} page {best_match.page_code}")

        return response

    def _error_response(
        self, 
        error_code: ErrorCode, 
        ocr_texts: Optional[List[str]] = None,
        spec_codes: Optional[List[str]] = None,
        page_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        生成错误响应，包含详细的识别信息
        
        Args:
            error_code: 错误码
            ocr_texts: OCR识别到的所有文本
            spec_codes: 识别到的规范编号列表
            page_codes: 识别到的页码列表
        
        Returns:
            错误响应字典
        """
        response = {
            "success": False,
            "error_code": error_code.value,
            "message": ERROR_MESSAGES.get(error_code, "Unknown error"),
        }
        
        # 添加详细的识别信息
        details = {}
        
        if ocr_texts is not None:
            details["ocr_texts"] = ocr_texts
            details["ocr_count"] = len(ocr_texts)
        
        if spec_codes is not None:
            details["identified_spec_codes"] = spec_codes
            
        if page_codes is not None:
            details["identified_page_codes"] = page_codes
        
        if details:
            response["details"] = details
            
        return response

    def _process_with_llm(self, image: np.ndarray) -> Dict[str, Any]:
        """大模型识别流程（新增）"""
        try:
            if not self.llm_engine:
                return self._error_response(ErrorCode.LLM_NOT_CONFIGURED)
            
            logger.info("Processing with LLM...")
            llm_result = self.llm_engine.recognize(image)
            
            # 🔍 测试：打印LLM最终返回结果
            print("\n" + "="*80)
            print("[LLM FINAL RESULT IN PIPELINE]")
            print("="*80)
            print(f"success: {llm_result['success']}")
            print(f"spec_code: {llm_result.get('spec_code')}")
            print(f"page_code: {llm_result.get('page_code')}")
            print(f"confidence: {llm_result.get('confidence')}")
            print(f"reasoning: {llm_result.get('reasoning', 'N/A')[:100]}...")
            print("="*80 + "\n")
            
            if not llm_result["success"]:
                return {
                    "success": False,
                    "method": "llm",
                    "error_code": ErrorCode.NO_MATCH,
                    "message": "LLM failed to recognize spec code or page code",
                    "details": llm_result
                }
            
            # 查找对应的PDF文件
            pdf_file = self.file_index.find_file(
                llm_result["spec_code"],
                llm_result["page_code"]
            )
            
            response = {
                "success": True,
                "method": "llm",
                "spec": {
                    "code": llm_result["spec_code"],
                    "page": llm_result["page_code"],
                    "confidence": llm_result["confidence"],
                },
                "metadata": {
                    "llm_reasoning": llm_result.get("reasoning", "")
                }
            }
            
            if pdf_file:
                response["file"] = {
                    "path": pdf_file.file_path,
                    "name": pdf_file.file_name,
                    "directory": pdf_file.directory,
                    "download_url": f"/api/download/{llm_result['spec_code']}/{llm_result['page_code']}"
                }
                response["file_found"] = True
            else:
                response["file"] = None
                response["file_found"] = False
                response["warning"] = f"识别成功：{llm_result['spec_code']} {llm_result['page_code']}，但数据库中未找到对应文件"
            
            return response
            
        except Exception as e:
            logger.error(f"LLM Pipeline error: {e}", exc_info=True)
            return self._error_response(ErrorCode.INTERNAL_ERROR)

    def _process_hybrid(self, image: np.ndarray) -> Dict[str, Any]:
        """混合识别流程：先OCR，低置信度时尝试LLM（新增）"""
        logger.info("Processing with hybrid strategy...")
        
        # 1. 先尝试OCR
        ocr_result = self._process_with_ocr(image)
        
        # 2. 检查OCR置信度
        ocr_confidence = ocr_result.get("spec", {}).get("confidence", 0.0)
        logger.info(f"OCR confidence: {ocr_confidence}")
        
        # 3. 如果OCR置信度足够高，直接返回
        if ocr_result["success"] and ocr_confidence >= LLMConfig.OCR_CONFIDENCE_THRESHOLD:
            logger.info("OCR confidence is high enough, using OCR result")
            ocr_result["method"] = "ocr"
            return ocr_result
        
        # 4. OCR置信度低，尝试LLM
        logger.info("OCR confidence is low, trying LLM...")
        if self.llm_engine:
            llm_result = self._process_with_llm(image)
            
            if llm_result["success"]:
                if "metadata" not in llm_result:
                    llm_result["metadata"] = {}
                llm_result["metadata"]["ocr_confidence"] = ocr_confidence
                llm_result["metadata"]["fallback_reason"] = "low_ocr_confidence"
                return llm_result
        
        # 5. LLM也失败，返回OCR结果（带降级标记）
        logger.warning("LLM also failed, returning OCR result")
        ocr_result["method"] = "ocr"
        if "metadata" not in ocr_result:
            ocr_result["metadata"] = {}
        ocr_result["metadata"]["llm_attempted"] = True
        ocr_result["metadata"]["llm_failed"] = True
        return ocr_result
