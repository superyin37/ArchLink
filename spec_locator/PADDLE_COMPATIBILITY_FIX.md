# 🔍 PaddleOCR Paddle 框架不兼容问题诊断

**错误时间**: 2026-01-16 15:38:06  
**错误代码**: `ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]`  
**根本原因**: PaddleOCR 和 Paddle 框架版本不兼容

---

## 📋 问题分析

### 错误日志
```
[2026-01-16 15:38:06,028] [ERROR] ocr_engine.py:109 - OCR recognition failed: 
(Unimplemented) ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]
(at ..\paddle\fluid\framework\new_executor\instruction\onednn\onednn_instruction.cc:118)
```

### 错误原因
这是 Paddle 框架内部错误，表示：
- ❌ 模型使用了新的 PIR 属性格式
- ❌ 当前 Paddle 框架版本不支持该格式
- ❌ 通常发生在旧版本 Paddle 尝试加载新版本模型时

### 影响
- OCR 初始化成功，但第一次推理时失败
- 返回空的识别结果

---

## 🛠️ 解决方案

### 方案 1: 更新到兼容版本（推荐）

```bash
# 激活虚拟环境
cd D:\projects\liuzong\spec_locator
.\.venv\Scripts\Activate.ps1

# 升级 PaddleOCR 和 Paddle 到最新版本
pip install --upgrade paddleocr paddle

# 或指定已知兼容版本
pip install paddleocr==2.7.0 paddle==2.5.1
```

### 方案 2: 降级到稳定版本

```bash
# 如果升级不稳定，尝试降级到旧版本
pip install paddleocr==2.6.0 paddle==2.4.2
```

### 方案 3: 禁用高级特性（快速修复）

已在代码中自动实现降级策略，按顺序尝试：

1. **新 API + 角度分类** → 新版本 PaddleOCR + GPU/CPU
2. **新 API - 角度分类** → 禁用角度分类，解决框架不兼容
3. **旧 API + 角度分类** → 旧版本 PaddleOCR
4. **旧 API - 角度分类** → 旧版本 + 禁用角度分类

---

## 📊 版本兼容性矩阵

| PaddleOCR | Paddle | 状态 | 备注 |
|-----------|--------|------|------|
| 2.7.0+ | 2.5.0+ | ✅ 推荐 | 支持 PIR 格式 |
| 2.6.0 | 2.4.0+ | ✅ 稳定 | 无 PIR 问题 |
| 2.5.0 | 2.3.0+ | ⚠️ 较旧 | 功能较少 |
| 不匹配 | - | ❌ 错误 | 会出现此错误 |

---

## 🔧 已实施的改进

### 文件: [ocr/ocr_engine.py](ocr/ocr_engine.py)

#### 改进 1: 多层降级初始化
```python
def _initialize_ocr(self):
    """
    初始化 PaddleOCR，包含多层降级策略
    
    降级顺序：
    1. 新 API + use_angle_cls=True
    2. 新 API + use_angle_cls=False（如果有框架不兼容）
    3. 旧 API + use_angle_cls=True
    4. 旧 API + use_angle_cls=False
    """
```

#### 改进 2: 增强错误提示
```python
def recognize(self, image: np.ndarray) -> List[TextBox]:
    # ...
    except Exception as e:
        logger.error(f"OCR recognition failed: {e}")
        logger.warning("Troubleshooting tips:")
        logger.warning("  1. Upgrade PaddleOCR: pip install --upgrade paddleocr paddle")
        logger.warning("  2. Or downgrade: pip install paddleocr==2.6.0 paddle==2.5.0")
        logger.warning("  3. Check CUDA compatibility if using GPU")
        logger.warning("  4. Try CPU mode by initializing with use_gpu=False")
        return []
```

---

## 🧪 测试步骤

### 1. 检查当前版本
```bash
python -c "import paddle; import paddleocr; print(f'Paddle: {paddle.__version__}'); print(f'PaddleOCR: {paddleocr.__version__}')"
```

### 2. 运行诊断
```bash
# 启动服务
python main.py

# 在另一个终端测试
curl -X POST http://localhost:8000/api/spec-locate -F "file=@cad_example_01.png"
```

### 3. 查看日志
```
# 查看初始化日志，确认使用哪个降级策略
# 查看识别日志，确认是否成功或有哪些建议
```

---

## 💡 快速诊断命令

```bash
# 查看 PaddleOCR 安装信息
pip show paddleocr paddle

# 测试 PaddleOCR 是否可用
python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(use_angle_cls=False); print('✓ PaddleOCR works!')"

# 查看详细日志
# 重新启动服务并观察初始化过程中的日志输出
```

---

## 🎯 推荐行动

1. **立即**: 尝试方案 3（自动降级，已实施）
2. **短期**: 升级到兼容版本（方案 1）
3. **监控**: 观察日志，确认使用的降级策略
4. **后续**: 如果问题持续，使用方案 2

---

## 📝 相关资源

- [PaddleOCR GitHub](https://github.com/PaddlePaddle/PaddleOCR)
- [Paddle 框架 Issues](https://github.com/PaddlePaddle/Paddle/issues)
- 检查该错误是否已在新版本中修复

---

**修复状态**: ✅ 已自动实现多层降级  
**测试状态**: 待验证  
**下一步**: 重启服务并测试 OCR 功能
