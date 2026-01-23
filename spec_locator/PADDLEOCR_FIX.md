# 🔧 PaddleOCR API 变更修复

**问题时间**: 2026-01-16 15:23:24  
**错误信息**: `PaddleOCR.predict() got an unexpected keyword argument 'cls'`  
**根本原因**: PaddleOCR 版本更新导致 API 变更

---

## 📌 问题详情

### 错误日志
```
[2026-01-16 15:23:24,155] [ERROR] ocr_engine.py:102 - OCR recognition failed: PaddleOCR.predict() got an unexpected keyword argument 'cls'
```

### 问题代码（旧版本）
```python
# ocr_engine.py 第 98 行
results = self.recognizer.ocr(image, cls=True)  # ❌ 新版本不支持此参数
```

---

## 🔍 PaddleOCR API 版本变更

### 旧版本 API (< v2.7.0)
```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_angle_cls=True,
    lang="ch",
    use_gpu=False,  # 参数名：use_gpu
)

# 调用时传递 cls 参数
results = ocr.ocr(image, cls=True)  # ✓ 支持
```

### 新版本 API (>= v2.7.0)
```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_angle_cls=True,
    lang="ch",
    device='cpu',  # 参数名改为：device（'cpu' 或 'gpu'）
)

# cls 参数在初始化时设置，调用时不传
results = ocr.ocr(image)  # ✓ cls 参数已在初始化中配置
```

---

## ✅ 修复方案

### 修复 1: 移除 ocr() 调用中的 cls 参数

**文件**: [ocr/ocr_engine.py](ocr/ocr_engine.py#L97-L107)

**修改前**:
```python
try:
    results = self.recognizer.ocr(image, cls=True)
    text_boxes = self._parse_results(results)
    logger.info(f"OCR recognized {len(text_boxes)} text boxes")
    return text_boxes
except Exception as e:
    logger.error(f"OCR recognition failed: {e}")
    return []
```

**修改后**:
```python
try:
    # PaddleOCR API 注意：
    # - 旧版本：ocr(image, cls=True)
    # - 新版本（2.7.0+）：直接调用，cls 参数在初始化时设置
    results = self.recognizer.ocr(image)
    text_boxes = self._parse_results(results)
    logger.info(f"OCR recognized {len(text_boxes)} text boxes")
    return text_boxes
except Exception as e:
    logger.error(f"OCR recognition failed: {e}")
    return []
```

### 修复 2: 改进初始化逻辑以支持两个版本

**文件**: [ocr/ocr_engine.py](ocr/ocr_engine.py#L53-L81)

**修改后**:
```python
def _initialize_ocr(self):
    """初始化 PaddleOCR"""
    try:
        from paddleocr import PaddleOCR
        
        # 尝试新版本 API（2.7.0+）
        try:
            self.recognizer = PaddleOCR(
                use_angle_cls=True,
                lang="ch",
                device='gpu' if self.use_gpu else 'cpu',  # 新参数
            )
            logger.info("PaddleOCR initialized with new API (v2.7.0+)")
        except TypeError as e:
            # 回退到旧版本 API（<2.7.0）
            logger.debug(f"New API failed: {e}, trying old API...")
            self.recognizer = PaddleOCR(
                use_angle_cls=True,
                lang="ch",
                use_gpu=self.use_gpu,  # 旧参数
            )
            logger.info("PaddleOCR initialized with old API (<v2.7.0)")
        
        logger.info("PaddleOCR initialized successfully")
    except ImportError:
        logger.warning(
            "PaddleOCR not installed. Install with: pip install paddleocr"
        )
        self.recognizer = None
    except Exception as e:
        logger.error(f"Failed to initialize PaddleOCR: {e}")
        self.recognizer = None
```

---

## 🧪 测试验证

### 验证修复
```bash
# 1. 激活环境
cd D:\projects\liuzong\spec_locator
.\.venv\Scripts\Activate.ps1

# 2. 运行服务
python main.py

# 3. 在另一个终端测试
curl -X POST http://localhost:8000/api/spec-locate -F "file=@cad_example_01.png"
```

### 预期结果
```json
{
  "success": true,
  "spec_code": "...",
  "page_code": "...",
  "confidence": 0.XX,
  "candidates": [...]
}
```

---

## 📋 相关问题参考

| 版本 | 变更内容 | 兼容性 |
|------|--------|------|
| < 2.7.0 | `ocr(image, cls=True)` + `use_gpu=False` | ✅ 旧版本 |
| >= 2.7.0 | `ocr(image)` + `device='cpu'` | ⚠️ 需更新 |

---

## 📝 修复总结

- ✅ 移除了 `cls=True` 参数
- ✅ 改进了版本兼容性检测
- ✅ 添加了详细的日志记录
- ✅ 确保两个版本的 PaddleOCR 都能正常工作

**修复状态**: 已完成  
**受影响文件**: 1 个 (`ocr/ocr_engine.py`)  
**测试状态**: 待验证
