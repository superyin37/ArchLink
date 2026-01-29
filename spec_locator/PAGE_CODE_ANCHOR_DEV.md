# 页码识别模块开发文档（规范号锚点法）

## 1. 目的
本文档描述 CAD 截图场景下的页码识别方案，采用“规范号锚点（Spec Anchor）”作为定位中心，替代旧的拼接式页码解析逻辑，提高圆形标注结构中的稳定性与准确率。

适用范围：Spec Locator 系统页码识别模块重构与维护。

---

## 2. 背景
CAD 图纸页码常以圆形标注出现，存在以下稳定特征：
- 页码通常位于规范号（如 12J2、11J6）附近
- 圆形标注结构常分为上下两部分
- 上半部分可能为序号，下半部分为真实页码
- 有时仅存在下半部分

传统基于正则与拼接的方式在该场景下误识别率高，因此引入基于空间锚点的新策略。

---

## 3. 设计目标
### 3.1 功能目标
- 以规范号作为定位锚点
- 在局部区域内搜索页码候选
- 自动判断上下结构
- 稳定提取真实页码
- 不再进行 C11-2 等字符串拼接

### 3.2 工程目标
- 不引入额外深度学习模型
- 复用现有 OCR 与 Geometry 模块
- 易调参、易维护
- 与现有 FileIndex 模块兼容

---

## 4. 整体流程
```
OCR
 ↓
Spec Anchor Detection
 ↓
Local Candidate Search
 ↓
Layout Analysis
 ↓
Page Selection
 ↓
FileIndex Matching
```

涉及模块：
- OCREngine
- SpecAnchorExtractor
- PageByAnchorExtractor（新增）
- FileIndex

---

## 5. 核心概念
### 5.1 Spec Anchor（规范号锚点）
OCR 文本框中符合规范编号格式的文本框，例如：
```
12J2
11J6
23J909
```

### 5.2 Page Candidate（页码候选框）
位于锚点附近、符合页码格式的文本框，例如：
```
C11
54
A5
```

---

## 6. 算法设计
### 6.1 步骤 1：规范号识别
从 OCR TextBox 中提取规范号框。

匹配规则：
```regex
\d{2,3}[A-Z]\d+
```
（大小写不敏感）

输出：
```python
List[TextBox]  # anchor_boxes
```

### 6.2 步骤 2：邻域搜索
以 anchor 为中心，在给定半径 R 内搜索候选页码。

距离计算：
```python
d = geometry.calculate_distance(anchor, box)
```

推荐参数：
| 参数 | 建议值 |
| --- | --- |
| R | 80 ~ 150 px |

### 6.3 步骤 3：候选过滤
候选框需满足：
- 文本符合页码正则
- OCR 置信度高于阈值

页码正则示例：
```regex
[A-Z]?\d+
```

置信度建议：
```
confidence >= 0.5
```

### 6.4 步骤 4：候选排序
按距离排序：
```python
candidates.sort(key=lambda b: dist(anchor, b))
```
仅保留前 1~2 个候选。

### 6.5 步骤 5：上下结构判断
当存在两个候选时，判断是否为上下排列：
```python
abs(x1 - x2) < X_THRESH
abs(y1 - y2) > Y_THRESH
```

推荐参数：
| 参数 | 建议值 |
| --- | --- |
| X_THRESH | 15 px |
| Y_THRESH | 20 px |

### 6.6 步骤 6：页码选择
- **上下双候选**：选择 $y$ 坐标更大的文本框
- **单候选**：使用距离最近结果

### 6.7 步骤 7：置信度融合
推荐评分公式：
```python
score = confidence / (distance + eps)
```
用于多候选竞争排序。

### 6.8 步骤 8：回退机制
当锚点法失败时，回退原 PageCodeParser（旧逻辑）。

---

## 7. 模块接口设计
### 7.1 PageByAnchorExtractor
```python
class PageByAnchorExtractor:
    def extract(self, boxes: List[TextBox]) -> List[PageCode]:
        pass
```

### 7.2 数据结构
```python
@dataclass
class PageCode:
    page: str
    confidence: float
    source_indices: List[int]
```

---

## 8. 参考实现伪代码
```python
def extract_by_anchor(boxes):
    anchors = find_anchors(boxes)
    results = []

    for a in anchors:
        nearby = []
        for b in boxes:
            if dist(a, b) < R and is_page_like(b.text):
                nearby.append(b)

        if not nearby:
            continue

        nearby.sort(key=lambda b: dist(a, b))
        top = nearby[:2]

        if len(top) == 2 and is_vertical_pair(top):
            page_box = bottom(top)
        else:
            page_box = top[0]

        results.append(PageCode(
            page=page_box.text,
            confidence=page_box.confidence,
            source_indices=[page_box.index]
        ))

    return results
```

---

## 9. 与现有系统集成
推荐流水线：
```
OCR
 ↓
PageByAnchorExtractor (Primary)
 ↓
PageCodeParser (Fallback)
 ↓
FileIndex
```

---

## 10. 参数调优建议
| 参数 | 作用 | 建议范围 |
| --- | --- | --- |
| R | 搜索半径 | 80~150 |
| X_THRESH | 垂直判断 | 10~20 |
| Y_THRESH | 垂直判断 | 15~30 |
| conf_min | 最低置信度 | 0.4~0.6 |

---

## 11. 异常场景处理
### 11.1 多锚点冲突
- 允许多个 PageCode
- 后续通过 FileIndex 再过滤

### 11.2 OCR 漏检
- 回退旧解析器
- 输出日志

### 11.3 干扰数字
- 强化距离与方向约束
- 引入字体大小过滤

---

## 12. 性能分析
时间复杂度：
```
O(N * K)
```
其中 $N$ 为 OCR box 数量，$K$ 为 anchor 数量。典型场景 $N < 100$，性能充足。

---

## 13. 测试方案
### 13.1 单元测试
- 标准圆标注样例
- 单下半样例
- 干扰数字样例

### 13.2 集成测试
- OCR → PDF 完整链路
- 回退逻辑验证

---

## 14. 后续优化方向
- 多页码层级支持
- OCR 二次裁剪
- 动态半径调整
- 统计学习评分模型

---

## 15. 总结
本方案基于规范号锚点进行页码定位，结合局部空间关系与上下结构判别，实现对 CAD 圆形标注页码的稳定识别。相比传统拼接方法，该方案在准确率、鲁棒性与可维护性方面更优，适合作为当前系统主解析策略。
