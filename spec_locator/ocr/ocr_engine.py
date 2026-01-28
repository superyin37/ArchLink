"""
OCR 引擎封装模块
- 集成 PaddleOCR
- 输出带有位置信息的文本结果
- 支持懒加载模式（首次使用时才加载模型）
"""

import logging
import threading
from typing import List, Dict, Tuple, Any
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextBox:
    """文本框数据结构"""
    text: str
    confidence: float
    bbox: Tuple[Tuple[int, int], ...]  # 四个角的坐标

    def get_center(self) -> Tuple[float, float]:
        """获取文本框中心点"""
        xs = [p[0] for p in self.bbox]
        ys = [p[1] for p in self.bbox]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def get_width(self) -> float:
        """获取文本框宽度"""
        return max(p[0] for p in self.bbox) - min(p[0] for p in self.bbox)

    def get_height(self) -> float:
        """获取文本框高度"""
        return max(p[1] for p in self.bbox) - min(p[1] for p in self.bbox)


class OCREngine:
    """OCR 引擎（支持懒加载）"""

    def __init__(self, use_gpu: bool = True, conf_threshold: float = 0.3, lazy_load: bool = True):
        """
        初始化 OCR 引擎（懒加载模式）

        Args:
            use_gpu: 是否使用 GPU
            conf_threshold: 置信度阈值
            lazy_load: 是否使用懒加载（默认True，首次使用时才加载模型）
        """
        self.use_gpu = use_gpu
        self.conf_threshold = conf_threshold
        self.recognizer = None
        self._initialized = False  # 标记是否已初始化
        self._init_lock = threading.Lock()  # 线程锁，确保线程安全
        
        if lazy_load:
            logger.info("OCREngine 创建（懒加载模式，模型将在首次使用时加载）")
        else:
            logger.info("OCREngine 创建（立即加载模式）")
            self._initialize_ocr()
            self._initialized = True

    def _initialize_ocr(self):
        """
        初始化 PaddleOCR，包含多层降级策略
        
        降级顺序：
        1. 新 API + use_angle_cls=True
        2. 新 API + use_angle_cls=False（如果有框架不兼容）
        3. 旧 API + use_angle_cls=True
        4. 旧 API + use_angle_cls=False
        """
        try:
            from paddleocr import PaddleOCR
            
            # 策略 1: 尝试新版本 API（2.7.0+）+ 角度分类 + 禁用OneDNN优化
            try:
                logger.info("Attempting PaddleOCR v2.7.0+ API with angle classification (OneDNN disabled)...")
                self.recognizer = PaddleOCR(
                    use_angle_cls=True,
                    lang="ch",
                    device='gpu' if self.use_gpu else 'cpu',
                    enable_mkldnn=False,  # 禁用OneDNN/MKL-DNN优化，避免PIR兼容性问题
                    use_mp=False,  # 禁用多进程
                )
                logger.info("✓ PaddleOCR initialized with new API (v2.7.0+) + angle_cls (OneDNN disabled)")
                return
            except TypeError as e:
                logger.debug(f"New API with device parameter not supported: {e}")
            except Exception as e:
                logger.debug(f"New API + angle_cls failed: {e}")
            
            # 策略 2: 新版本 API（2.7.0+）- 禁用角度分类（如果有 Paddle 框架不兼容）
            try:
                logger.info("Attempting PaddleOCR v2.7.0+ API without angle classification...")
                self.recognizer = PaddleOCR(
                    use_angle_cls=False,
                    lang="ch",
                    device='gpu' if self.use_gpu else 'cpu',
                )
                logger.warning("⚠ PaddleOCR initialized with new API - angle classification disabled")
                return
            except TypeError as e:
                logger.debug(f"New API attempt 2 failed: {e}")
            except Exception as e:
                logger.debug(f"New API without angle_cls failed: {e}")
            
            # 策略 3: 旧版本 API（<2.7.0）+ 角度分类
            try:
                logger.info("Attempting PaddleOCR old API (<v2.7.0) with angle classification...")
                self.recognizer = PaddleOCR(
                    use_angle_cls=True,
                    lang="ch",
                    use_gpu=self.use_gpu,
                )
                logger.info("✓ PaddleOCR initialized with old API (<v2.7.0) + angle_cls")
                return
            except TypeError as e:
                logger.debug(f"Old API with angle_cls not supported: {e}")
            except Exception as e:
                logger.debug(f"Old API + angle_cls failed: {e}")
            
            # 策略 4: 旧版本 API（<2.7.0）- 禁用角度分类
            try:
                logger.info("Attempting PaddleOCR old API without angle classification...")
                self.recognizer = PaddleOCR(
                    use_angle_cls=False,
                    lang="ch",
                    use_gpu=self.use_gpu,
                )
                logger.warning("⚠ PaddleOCR initialized with old API - angle classification disabled")
                return
            except Exception as e:
                logger.error(f"Old API without angle_cls also failed: {e}")
            
            # 所有策略都失败
            logger.error("All PaddleOCR initialization strategies failed")
            self.recognizer = None
            
        except ImportError:
            logger.warning(
                "PaddleOCR not installed. Install with: pip install paddleocr paddle"
            )
            self.recognizer = None
        except Exception as e:
            logger.error(f"Unexpected error during PaddleOCR initialization: {e}")
            self.recognizer = None

    def _ensure_initialized(self):
        """
        确保 OCR 已初始化（懒加载入口点）
        使用双重检查锁定模式确保线程安全
        """
        if self._initialized:
            return
        
        with self._init_lock:
            # 双重检查：避免多线程重复初始化
            if self._initialized:
                return
            
            logger.info("首次使用 OCR，开始加载模型...")
            self._initialize_ocr()
            self._initialized = True
            logger.info("✓ OCR 模型加载完成")
    
    def warmup(self):
        """
        预热方法：主动触发模型加载（可选）
        可在后台线程或 FastAPI lifespan 中调用
        """
        logger.info("OCR 预热：主动加载模型...")
        self._ensure_initialized()
        logger.info("✓ OCR 预热完成")
    
    def recognize(self, image: np.ndarray) -> List[TextBox]:
        """
        识别图像中的文本（懒加载版本）

        Args:
            image: 输入图像（BGR 或灰度格式）

        Returns:
            文本框列表
        """
        # 懒加载：首次调用时才初始化
        self._ensure_initialized()
        
        if self.recognizer is None:
            logger.error("OCR engine 初始化失败")
            return []

        try:
            # PaddleOCR API 注意：
            # - 旧版本：ocr(image, cls=True)
            # - 新版本（2.7.0+）：直接调用，cls 参数在初始化时设置
            results = self.recognizer.ocr(image)
            print(f"DEBUG: PaddleOCR 原始返回内容: {results}")
            text_boxes = self._parse_results(results)
            logger.info(f"OCR recognized {len(text_boxes)} text boxes")
            return text_boxes
        except Exception as e:
            logger.error(f"OCR recognition failed: {e}")
            logger.warning("Troubleshooting tips:")
            logger.warning("  1. Upgrade PaddleOCR: pip install --upgrade paddleocr paddle")
            logger.warning("  2. Or downgrade: pip install paddleocr==2.6.0 paddle==2.5.0")
            logger.warning("  3. Check CUDA compatibility if using GPU")
            logger.warning("  4. Try CPU mode by initializing with use_gpu=False")
            return []

    def _parse_results(self, results: List[Any]) -> List[TextBox]:
        """
        解析 PaddleOCR 返回结果，支持多种返回格式以兼容不同版本

        Args:
            results: PaddleOCR 返回的原始结果（不同版本格式可能不同）

        Returns:
            TextBox 列表
        """
        text_boxes = []

        if not results:
            return text_boxes

        # 有的版本会将结果包在多层列表中（e.g., [[[[bbox,...]]]]），需要递归查找最靠近“行”结构的列表
        def _is_line(item):
            # 判断一个元素是否像 OCR 的“行”结构：
            # - dict （例如 {'text':..., 'score':..., 'bbox':...}）
            # - list/tuple，且第二个元素应当是文本(或(text,score) 结构)或 dict（避免把纯 bbox 列表误判为行）
            if isinstance(item, dict):
                return True
            if not isinstance(item, (list, tuple)):
                return False
            if len(item) < 2:
                return False
            second = item[1]
            if isinstance(second, str):
                return True
            if isinstance(second, (list, tuple)):
                # 常见情况：(bbox, (text, score)) 或 (bbox, text, score)
                # 如果第二项是 (text, score) tuple，认为是行
                # 如果第二项本身是 bbox（平坦数字列表），则不视为行
                # 因此对第二项若是 tuple/list 并且包含字符串则判为行
                if any(isinstance(v, str) for v in second if isinstance(second, (list, tuple))):
                    return True
                # 若第二项为 (text,score) 结构并且第二项的第一个元素为字符串
                try:
                    if isinstance(second[0], str):
                        return True
                except Exception:
                    pass
            if isinstance(second, dict):
                return True
            return False

        def _find_candidate(obj):
            # 递归查找包含若干行的列表并返回该列表
            if isinstance(obj, (list, tuple)):
                if len(obj) > 0 and all(_is_line(el) for el in obj):
                    return list(obj)
                for el in obj:
                    found = _find_candidate(el)
                    if found:
                        return found
            return []

        candidate_list = _find_candidate(results)

        for line in candidate_list:
            try:
                bbox = None
                text = ""
                confidence = 0.0

                # 常见格式 1: (bbox, (text, confidence))
                # 常见格式 2: (bbox, text, confidence)
                # 常见格式 3: dict 或其他结构
                if isinstance(line, (list, tuple)):
                    if len(line) == 2:
                        bbox_part, res_part = line
                        bbox = bbox_part
                        if isinstance(res_part, (list, tuple)) and len(res_part) == 2 and isinstance(res_part[0], str):
                            text, confidence = res_part
                        elif isinstance(res_part, str):
                            text = res_part
                            confidence = 0.0
                        elif isinstance(res_part, dict):
                            text = res_part.get("text", "")
                            confidence = res_part.get("score", 0.0)
                        else:
                            text = str(res_part)
                            confidence = 0.0
                    elif len(line) >= 3:
                        bbox = line[0]
                        text = line[1]
                        confidence = line[2]
                    else:
                        logger.debug(f"Unrecognized OCR line format: {line}")
                        continue
                elif isinstance(line, dict):
                    bbox = line.get("bbox")
                    text = line.get("text") or line.get("label") or ""
                    confidence = line.get("score") or line.get("confidence") or 0.0
                else:
                    logger.debug(f"Unrecognized OCR line type: {type(line)}")
                    continue

                # 规范化 bbox 到 ((x1,y1),(x2,y2),(x3,y3),(x4,y4))
                if bbox is None:
                    continue

                if isinstance(bbox, (list, tuple, np.ndarray)):
                    # 平坦坐标列表，如 [x1,y1,x2,y2,...]
                    if len(bbox) >= 8 and not isinstance(bbox[0], (list, tuple, np.ndarray)):
                        coords = [int(float(v)) for v in bbox[:8]]
                        bbox_tuple = tuple((coords[i], coords[i + 1]) for i in range(0, 8, 2))
                    else:
                        pts = []
                        for p in bbox:
                            if isinstance(p, (list, tuple, np.ndarray)) and len(p) >= 2:
                                pts.append((int(float(p[0])), int(float(p[1]))))
                        bbox_tuple = tuple(pts)
                else:
                    logger.debug(f"Unrecognized bbox type: {type(bbox)}")
                    continue

                try:
                    confidence = float(confidence)
                except Exception:
                    confidence = 0.0

                if text and confidence >= self.conf_threshold:
                    text_box = TextBox(text=str(text).strip(), confidence=confidence, bbox=bbox_tuple)
                    text_boxes.append(text_box)

            except Exception as e:
                logger.debug(f"Could not parse OCR line: {line} - {e}")
                continue

        # 按位置排序（从上到下，从左到右）
        text_boxes.sort(key=lambda tb: (tb.get_center()[1], tb.get_center()[0]))

        return text_boxes

    def get_all_text(self, image: np.ndarray) -> str:
        """获取图像中的全部文本"""
        text_boxes = self.recognize(image)
        return "\\n".join([tb.text for tb in text_boxes])
