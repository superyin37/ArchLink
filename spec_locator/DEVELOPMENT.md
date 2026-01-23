"""
快速开发指南

本文件说明如何快速搭建和开发 Spec Locator Service
"""

# ============================================================================
# 快速开始
# ============================================================================

## 1. 环境准备

### 方式 A：使用 pip（推荐用于简单开发）

```bash
# 克隆或进入项目目录
cd spec_locator

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -e ".[dev]"
```

### 方式 B：使用 uv（推荐用于快速开发，比 pip 快 10-100 倍）

```bash
# 安装 uv（如果还没安装）
pip install uv
# 或使用官方安装脚本
# Linux/macOS:   curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows:       powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 创建虚拟环境并安装依赖
cd spec_locator
uv venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
uv pip install -e ".[dev]"

# 或一条命令搞定
uv sync --dev
```

## 2. 启动服务

```bash
# 方式 1：运行主程序
python main.py

# 方式 2：使用 uvicorn（支持热重载）
uvicorn api.server:app --reload
```

## 3. 测试 API

```bash
# 健康检查
curl http://localhost:8000/health

# 上传图片进行识别
curl -X POST http://localhost:8000/api/spec-locate -F "file=@sample.png"
```

# ============================================================================
# 项目结构说明
# ============================================================================

```
spec_locator/
├── api/                     # HTTP API 层
│   ├── __init__.py
│   └── server.py            # FastAPI 应用
│
├── config/                  # 配置管理
│   ├── __init__.py
│   └── config.py            # 全局配置
│
├── core/                    # 核心流水线
│   ├── __init__.py
│   └── pipeline.py          # 主处理流程
│
├── ocr/                     # OCR 引擎
│   ├── __init__.py
│   └── ocr_engine.py        # PaddleOCR 封装
│
├── parser/                  # 解析层
│   ├── __init__.py
│   ├── geometry.py          # 几何关系计算
│   ├── page_code.py         # 页码识别
│   └── spec_code.py         # 规范编号识别
│
├── postprocess/             # 后处理
│   ├── __init__.py
│   └── confidence.py        # 置信度评估
│
├── preprocess/              # 预处理
│   ├── __init__.py
│   └── image_preprocess.py  # 图像处理
│
├── tests/                   # 测试
│   ├── __init__.py
│   ├── test_geometry.py
│   └── test_spec_code.py
│
├── examples.py              # 使用示例
├── main.py                  # 程序入口
├── pyproject.toml           # 项目元数据
└── README_DEV.md            # 开发文档
```

# ============================================================================
# 核心数据流
# ============================================================================

输入 (图像)
    ↓
[预处理] ImagePreprocessor.preprocess()
    • 灰度化、二值化
    • 去除 CAD 结构线
    • 增强对比度
    ↓
[OCR] OCREngine.recognize()
    • 使用 PaddleOCR 识别文本
    • 返回 TextBox 列表 (text + bbox + confidence)
    ↓
[规范编号解析] SpecCodeParser.parse()
    • 正则匹配规范编号
    • 字符修正与验证
    • 返回 SpecCode 列表
    ↓
[页码识别] PageCodeParser.parse()
    • 识别页码前缀 (如 C11)
    • 识别页码后缀 (如 2)
    • 利用几何关系组合
    • 返回 PageCode 列表
    ↓
[后处理] ConfidenceEvaluator.evaluate()
    • 配对规范编号和页码
    • 计算综合置信度
    • 排序候选结果
    • 返回 SpecMatch 列表
    ↓
输出 (JSON)
    {
      "success": true,
      "spec": {...},
      "candidates": [...]
    }

# ============================================================================
# 关键类和方法
# ============================================================================

## ImagePreprocessor
- preprocess(image) → 预处理后的图像
- _resize_image(image) → 缩放图像
- _remove_lines(gray) → 去除结构线
- _enhance_contrast(gray) → 增强对比度
- _binarize(gray) → 二值化

## OCREngine
- recognize(image) → List[TextBox]
- _parse_results(results) → 解析原始结果

## TextBox
- .text: 识别的文本
- .confidence: 置信度
- .bbox: 四个角的坐标
- .get_center() → (x, y)
- .get_width() → 宽度
- .get_height() → 高度

## SpecCodeParser
- parse(text_boxes) → List[SpecCode]
- _extract_spec_code(text) → 提取规范编号
- _validate_spec_code(code) → 验证有效性

## PageCodeParser
- parse(text_boxes) → List[PageCode]
- _extract_page_parts(text_boxes) → 提取页码部分
- _combine_page_parts(parts, boxes) → 组合页码

## GeometryCalculator
- calculate_distance(box1, box2) → 欧氏距离
- get_direction(box1, box2) → 相对方向
- find_neighbors(boxes, target_idx) → 查找相邻框
- find_aligned(boxes, ref_idx, direction) → 查找对齐框

## ConfidenceEvaluator
- evaluate(specs, pages) → List[SpecMatch]
- _calculate_confidence(spec, page) → 置信度

## SpecLocatorPipeline
- process(image) → 处理结果字典

# ============================================================================
# 开发常见任务
# ============================================================================

### 任务 1: 添加新的规范编号类型

编辑 config/config.py：
```python
SPEC_CODE_PATTERN = r"(...)"  # 更新正则表达式
SpecCodeParser.VALID_PREFIXES.add("31")  # 添加新前缀
```

### 任务 2: 改进页码识别

编辑 parser/page_code.py：
```python
def _combine_page_parts(self, page_parts, text_boxes):
    # 优化组合逻辑
    # 例如调整最大搜索距离、方向判定等
```

### 任务 3: 调整置信度权重

编辑 config/config.py：
```python
class ConfidenceConfig:
    OCR_WEIGHT = 0.6  # 提高 OCR 权重
    GEOMETRY_WEIGHT = 0.2
    PATTERN_WEIGHT = 0.2
```

### 任务 4: 添加调试输出

编辑 api/server.py 或 core/pipeline.py，添加日志：
```python
logger.debug(f"Debug info: {variable}")
```

### 任务 5: 添加新的测试

在 tests/ 目录下新建文件：
```python
# tests/test_new_feature.py
def test_something():
    assert True
```

运行测试：
```bash
pytest tests/test_new_feature.py -v
```

# ============================================================================
# 版本演进计划
# ============================================================================

### v1.0 (当前)
✓ 基础版本
✓ 单规范编号识别
✓ 单页码识别
✓ HTTP API 接口
✓ 模块化架构

### v1.1 (计划中)
□ 多规范编号同时识别
□ 支持多页码组合
□ 性能优化（缓存、批处理）
□ 更完善的错误恢复

### v1.2 (计划中)
□ 调试模式
□ OCR 可视化返回
□ 图像质量诊断
□ 识别过程追踪

### v2.0 (计划中)
□ 引入深度学习模型
□ 页码区域精准检测
□ 多语言支持
□ 更高的识别准确率

# ============================================================================
# 性能优化建议
# ============================================================================

1. **启用 GPU 加速**
   export OCR_USE_GPU=true
   需要安装 CUDA 和相应驱动

2. **使用缓存**
   在 PreprocessConfig 中缓存预处理的图像

3. **批量处理**
   支持一次上传多张图片

4. **模型量化**
   使用较小的 OCR 模型以加快速度

5. **异步处理**
   在 API 中使用异步任务队列（如 Celery）

# ============================================================================
# 调试技巧
# ============================================================================

### 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 可视化 OCR 结果
```python
from ocr import OCREngine
engine = OCREngine()
boxes = engine.recognize(image)

for box in boxes:
    x1, y1 = int(min(p[0] for p in box.bbox)), int(min(p[1] for p in box.bbox))
    x2, y2 = int(max(p[0] for p in box.bbox)), int(max(p[1] for p in box.bbox))
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(image, box.text, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0))

cv2.imshow("OCR Results", image)
cv2.waitKey(0)
```

### 测试单个模块
```bash
# 测试规范编号识别
python -m pytest tests/test_spec_code.py::TestSpecCodeParser::test_validate_spec_code -v

# 测试几何关系
python -m pytest tests/test_geometry.py -v
```

# ============================================================================
# 常见问题排查
# ============================================================================

问题 1: ImportError: No module named 'paddleocr'
→ 解决: pip install paddleocr

问题 2: 识别准确率低
→ 解决: 
  - 检查输入图像质量
  - 调整 PreprocessConfig.ENHANCE_CONTRAST
  - 提供更多训练数据

问题 3: 启动时内存不足
→ 解决:
  - 使用较小的 OCR 模型
  - 启用 GPU
  - 减少工作进程数

问题 4: API 返回 NO_MATCH
→ 解决:
  - 检查规范编号格式
  - 检查页码是否被正确识别
  - 降低 ConfidenceConfig.MIN_CONFIDENCE 阈值

# ============================================================================
# 联系方式
# ============================================================================

遇到问题或需要帮助？
- 查看 README_DEV.md
- 查看源码中的注释
- 运行 examples.py 了解使用方法
"""

if __name__ == "__main__":
    print(__doc__)
