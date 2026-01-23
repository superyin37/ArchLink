"""
图像预处理模块
- 灰度化、二值化
- 去除 CAD 结构线
- 提升文字区域对比度
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """图像预处理器"""

    def __init__(self, max_size: int = 4096, enhance_contrast: bool = True):
        """
        初始化预处理器

        Args:
            max_size: 最大图像尺寸
            enhance_contrast: 是否增强对比度
        """
        self.max_size = max_size
        self.enhance_contrast = enhance_contrast

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        主预处理流水线

        Args:
            image: 输入图像（BGR 格式）

        Returns:
            预处理后的图像
        """
        # 1. 尺寸检查与缩放
        image = self._resize_image(image)

        # 2. 灰度化
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 3. 去除结构线
        gray = self._remove_lines(gray)

        # 4. 增强对比度
        if self.enhance_contrast:
            gray = self._enhance_contrast(gray)

        # 5. 二值化
        binary = self._binarize(gray)

        return binary

    def _resize_image(self, image: np.ndarray) -> np.ndarray:
        """缩放图像以符合最大尺寸限制"""
        h, w = image.shape[:2]
        if max(h, w) > self.max_size:
            scale = self.max_size / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            logger.info(f"Resized image from {w}x{h} to {new_w}x{new_h}")
        return image

    def _remove_lines(self, gray: np.ndarray) -> np.ndarray:
        """
        去除 CAD 中的结构线和标注线

        使用形态学操作去除细线，保留文字
        """
        # 创建水平和竖直的结构元素
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))

        # 自适应阈值处理，更好地保留文字
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # 使用膨胀操作连接被分割的文字
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)

        logger.debug("Lines removed from image")
        return thresh

    def _enhance_contrast(self, gray: np.ndarray) -> np.ndarray:
        """
        增强对比度以提升 OCR 准确率

        使用 CLAHE (Contrast Limited Adaptive Histogram Equalization)
        """
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        logger.debug("Contrast enhanced")
        return enhanced

    def _binarize(self, gray: np.ndarray) -> np.ndarray:
        """
        二值化图像

        使用 Otsu 自动阈值
        """
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        logger.debug("Image binarized")
        return binary

    def get_text_regions(
        self, binary: np.ndarray, min_area: int = 100
    ) -> list:
        """
        提取文本区域的边界框

        Args:
            binary: 二值化图像
            min_area: 最小区域面积

        Returns:
            文本区域的边界框列表 [(x, y, w, h), ...]
        """
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        text_regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                text_regions.append((x, y, w, h))

        text_regions.sort(key=lambda r: (r[1], r[0]))  # 按位置排序
        logger.debug(f"Found {len(text_regions)} potential text regions")
        return text_regions
