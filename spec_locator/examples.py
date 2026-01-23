"""
使用示例脚本
展示如何使用 Spec Locator Service
"""

import sys
import os
import cv2
import numpy as np
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spec_locator.config import config
from spec_locator.core.pipeline import SpecLocatorPipeline
from spec_locator.preprocess import ImagePreprocessor
from spec_locator.ocr import OCREngine
from spec_locator.parser import SpecCodeParser, PageCodeParser


def example_1_full_pipeline():
    """示例 1：完整流水线处理"""
    print("\n" + "=" * 60)
    print("示例 1：完整流水线处理")
    print("=" * 60)

    # 假设有一张测试图像
    sample_image_path = "sample_image.png"

    if not os.path.exists(sample_image_path):
        print(f"⚠️  找不到示例图像: {sample_image_path}")
        print("   请放置一张 CAD 截图到项目根目录，命名为 sample_image.png")
        return

    # 读取图像
    image = cv2.imread(sample_image_path)
    if image is None:
        print("❌ 无法读取图像")
        return

    print(f"✓ 已读取图像: {sample_image_path}")
    print(f"  尺寸: {image.shape[1]}x{image.shape[0]}")

    # 初始化流水线
    pipeline = SpecLocatorPipeline(use_gpu=False)

    # 处理
    print("\n处理中...")
    result = pipeline.process(image)

    # 输出结果
    print("\n识别结果:")
    print("-" * 40)
    if result["success"]:
        spec = result["spec"]
        print(f"✓ 规范编号: {spec['code']}")
        print(f"  页码: {spec['page']}")
        print(f"  置信度: {spec['confidence']:.2%}")

        if result["candidates"]:
            print(f"\n候选结果（前 {len(result['candidates'])} 个）:")
            for i, candidate in enumerate(result["candidates"], 1):
                print(f"  {i}. {candidate['code']} - {candidate['page']} "
                      f"({candidate['confidence']:.2%})")
    else:
        print(f"❌ 识别失败")
        print(f"  错误码: {result['error_code']}")
        print(f"  错误信息: {result['message']}")


def example_2_individual_modules():
    """示例 2：单独使用各模块"""
    print("\n" + "=" * 60)
    print("示例 2：单独使用各模块")
    print("=" * 60)

    sample_image_path = "sample_image.png"

    if not os.path.exists(sample_image_path):
        print(f"⚠️  找不到示例图像: {sample_image_path}")
        return

    image = cv2.imread(sample_image_path)

    # 1. 预处理
    print("\n1. 图像预处理")
    print("-" * 40)
    preprocessor = ImagePreprocessor()
    processed_image = preprocessor.preprocess(image)
    print(f"✓ 预处理完成")
    print(f"  输入: {image.shape} (BGR)")
    print(f"  输出: {processed_image.shape} (二值化)")

    # 2. OCR
    print("\n2. OCR 识别")
    print("-" * 40)
    ocr_engine = OCREngine(use_gpu=False, conf_threshold=0.3)
    text_boxes = ocr_engine.recognize(image)
    print(f"✓ 识别完成: 找到 {len(text_boxes)} 个文本框")
    print("\n前 5 个识别结果:")
    for i, box in enumerate(text_boxes[:5], 1):
        print(f"  {i}. '{box.text}' (置信度: {box.confidence:.2%})")

    # 3. 规范编号解析
    print("\n3. 规范编号识别")
    print("-" * 40)
    spec_parser = SpecCodeParser()
    spec_codes = spec_parser.parse(text_boxes)
    print(f"✓ 识别完成: 找到 {len(spec_codes)} 个规范编号")
    for spec in spec_codes:
        print(f"  • {spec.code} (置信度: {spec.confidence:.2%})")

    # 4. 页码识别
    print("\n4. 页码识别")
    print("-" * 40)
    page_parser = PageCodeParser()
    page_codes = page_parser.parse(text_boxes)
    print(f"✓ 识别完成: 找到 {len(page_codes)} 个页码")
    for page in page_codes:
        print(f"  • {page.page} (置信度: {page.confidence:.2%})")


def example_3_geometry_relations():
    """示例 3：几何关系计算"""
    print("\n" + "=" * 60)
    print("示例 3：几何关系计算")
    print("=" * 60)

    from spec_locator.ocr.ocr_engine import TextBox
    from spec_locator.parser.geometry import GeometryCalculator

    # 创建示例文本框
    box1 = TextBox(
        text="12J2",
        confidence=0.95,
        bbox=((10, 10), (50, 10), (50, 30), (10, 30))
    )
    box2 = TextBox(
        text="C11",
        confidence=0.90,
        bbox=((60, 10), (90, 10), (90, 30), (60, 30))
    )
    box3 = TextBox(
        text="2",
        confidence=0.85,
        bbox=((100, 10), (110, 10), (110, 30), (100, 30))
    )

    boxes = [box1, box2, box3]

    # 计算几何关系
    calculator = GeometryCalculator()

    print("\n文本框信息:")
    for i, box in enumerate(boxes):
        print(f"  Box {i}: '{box.text}' 中心点={box.get_center()}")

    print("\n几何关系分析:")
    print("-" * 40)

    # box1 到 box2
    distance = calculator.calculate_distance(box1, box2)
    direction = calculator.get_direction(box1, box2)
    h_gap, v_gap = calculator.calculate_gaps(box1, box2)
    print(f"Box 0 -> Box 1:")
    print(f"  距离: {distance:.1f} px")
    print(f"  方向: {direction}")
    print(f"  间距: 水平={h_gap} px, 竖直={v_gap} px")

    # box1 到 box3
    distance = calculator.calculate_distance(box1, box3)
    direction = calculator.get_direction(box1, box3)
    h_gap, v_gap = calculator.calculate_gaps(box1, box3)
    print(f"\nBox 0 -> Box 2:")
    print(f"  距离: {distance:.1f} px")
    print(f"  方向: {direction}")
    print(f"  间距: 水平={h_gap} px, 竖直={v_gap} px")


def example_4_configuration():
    """示例 4：配置管理"""
    print("\n" + "=" * 60)
    print("示例 4：配置管理")
    print("=" * 60)

    print("\n当前配置:")
    print("-" * 40)

    from config import (
        OCRConfig,
        PreprocessConfig,
        GeometryConfig,
        ConfidenceConfig,
        APIConfig,
    )

    print(f"\nOCR 配置:")
    print(f"  • 使用 GPU: {OCRConfig.USE_GPU}")
    print(f"  • 置信度阈值: {OCRConfig.CONF_THRESHOLD}")
    print(f"  • 语言: {OCRConfig.LANGUAGE}")

    print(f"\n预处理配置:")
    print(f"  • 最大图像尺寸: {PreprocessConfig.MAX_IMAGE_SIZE}")
    print(f"  • 最小图像尺寸: {PreprocessConfig.MIN_IMAGE_SIZE}")
    print(f"  • 增强对比度: {PreprocessConfig.ENHANCE_CONTRAST}")

    print(f"\n几何关系配置:")
    print(f"  • 最大邻近距离: {GeometryConfig.MAX_DISTANCE} px")
    print(f"  • 方向容差: {GeometryConfig.DIRECTION_TOLERANCE}°")

    print(f"\n置信度配置:")
    print(f"  • OCR 权重: {ConfidenceConfig.OCR_WEIGHT}")
    print(f"  • 几何关系权重: {ConfidenceConfig.GEOMETRY_WEIGHT}")
    print(f"  • 模式匹配权重: {ConfidenceConfig.PATTERN_WEIGHT}")
    print(f"  • 最小置信度: {ConfidenceConfig.MIN_CONFIDENCE}")

    print(f"\nAPI 配置:")
    print(f"  • 主机: {APIConfig.HOST}")
    print(f"  • 端口: {APIConfig.PORT}")
    print(f"  • 工作进程数: {APIConfig.WORKERS}")
    print(f"  • 最大上传大小: {APIConfig.MAX_UPLOAD_SIZE / (1024*1024):.1f} MB")
    print(f"  • 允许的文件类型: {APIConfig.ALLOWED_EXTENSIONS}")


def main():
    """主程序"""
    print("\n" + "=" * 60)
    print("Spec Locator Service - 使用示例")
    print("=" * 60)

    print("\n可选的示例：")
    print("  1. 完整流水线处理")
    print("  2. 单独使用各模块")
    print("  3. 几何关系计算")
    print("  4. 配置管理")
    print("  0. 退出")

    choice = input("\n请选择示例 (0-4): ").strip()

    if choice == "1":
        example_1_full_pipeline()
    elif choice == "2":
        example_2_individual_modules()
    elif choice == "3":
        example_3_geometry_relations()
    elif choice == "4":
        example_4_configuration()
    elif choice == "0":
        print("退出")
        return
    else:
        print("❌ 无效的选择")
        return

    print("\n" + "=" * 60)
    print("✓ 示例完成")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
