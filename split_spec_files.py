import os
import re
import fitz  # PyMuPDF
from paddleocr import PaddleOCR
import numpy as np
import cv2

# =========================
# 环境检查（可选）
# =========================
print("NumPy:", np.__version__)   # 期望 1.26.4
print("OpenCV:", cv2.__version__)

# =========================
# 全局 OCR（只初始化一次），含多轮降级初始化以兼容不同 Paddle/PaddleOCR 版本
# =========================
def init_ocr():
    attempts = [
        {"use_textline_orientation": True, "lang": "ch"},
        {"use_textline_orientation": False, "lang": "ch"},
        {"lang": "ch"},
    ]

    for kw in attempts:
        try:
            o = PaddleOCR(**kw)
            print(f"✅ PaddleOCR initialized with {kw}")
            return o
        except TypeError as e:
            # 尝试更精简的参数集合，以兼容不同版本构造器签名
            reduced = {k: v for k, v in kw.items() if k in ("lang", "use_textline_orientation")}
            try:
                o = PaddleOCR(**reduced)
                print(f"✅ PaddleOCR initialized with reduced args {reduced}")
                return o
            except Exception as e2:
                print(f"⚠️ 初始化尝试失败：{kw} -> {e2}")
        except Exception as e:
            print(f"⚠️ 初始化尝试失败：{kw} -> {e}")

    raise RuntimeError("无法初始化 PaddleOCR，请检查环境")

ocr = init_ocr()

# =========================
# 左下角 ROI 裁剪
# =========================
def crop_left_bottom(img: np.ndarray) -> np.ndarray:
    """
    裁剪页面左下角区域（比例裁剪，适配不同分辨率）
    """
    h, w, _ = img.shape
    x1 = int(w * 0.80)
    x2 = w
    y1 = int(h * 0.80)
    y2 = h
    return img[y1:y2, x1:x2]

# =========================
# OCR 识别
# =========================
def ocr_text(img: np.ndarray) -> str:
    global ocr
    # 兼容不同版本 PaddleOCR API：早期使用 ocr(img, cls=False)，新版本使用 predict 或 ocr 不带 cls
    try:
        result = ocr.ocr(img, cls=False)
    except TypeError:
        try:
            result = ocr.ocr(img)
        except TypeError:
            # fallback to predict
            result = ocr.predict(img)
    except Exception as e:
        # 捕获运行时推理错误（如 paddle/paddlex 不兼容导致的 NotImplementedError）并尝试降级重试一次
        print(f"⚠️ OCR 推理失败：{e}")
        try:
            print("🔁 尝试使用降级配置重新初始化 PaddleOCR 并重试（use_angle_cls=False, use_textline_orientation=False）")
            ocr = PaddleOCR(lang="ch", use_angle_cls=False, use_textline_orientation=False)
            try:
                result = ocr.ocr(img)
            except TypeError:
                result = ocr.predict(img)
        except Exception as e2:
            print(f"❌ 降级重试失败：{e2}")
            return ""

    print("🧠 OCR raw result:")
    print(result)

    if not result:
        return ""

    def _extract_text_from_word(word):
        """兼容不同版本的 PaddleOCR 输出格式，从单个词条中提取文本"""
        # 常见格式： (bbox, (text, score)) 或 (bbox, text) 或 (bbox, text, score)
        try:
            if isinstance(word, (list, tuple)):
                if len(word) >= 2:
                    second = word[1]
                    # (bbox, (text, score))
                    if isinstance(second, (list, tuple)) and len(second) >= 1 and isinstance(second[0], str):
                        return second[0]
                    # (bbox, text)
                    if isinstance(second, str):
                        return second
                    # (bbox, text, score)
                    if len(word) >= 3 and isinstance(word[1], str):
                        return word[1]
                    # (bbox, {"text":..., "score":...})
                    if isinstance(second, dict):
                        return second.get("text") or second.get("label")
                # 有时 OCR 库会返回简单的 (text, score) 对
                if len(word) == 2 and isinstance(word[0], str):
                    return word[0]
            elif isinstance(word, dict):
                return word.get("text") or word.get("label")
            elif isinstance(word, str):
                return word
        except Exception:
            return None
        return None

    texts = []
    for line in result:
        if not line:
            continue
        for word in line:
            txt = _extract_text_from_word(word)
            if txt:
                texts.append(txt)

    text = " ".join(texts)

    print("📝 OCR merged text:")
    print(text)

    return text

# =========================
# 页码提取（多模式）
# =========================
PAGE_PATTERNS = [
    # 支持字母-数字范围，如 B-12
    r"\b[A-Z]+\s*-\s*\d+\b",
    # 支持字母+数字，如 A1
    r"\b[A-Z]+\d+\b",
    # 数字范围，如 5-9
    r"\b\d+\s*-\s*\d+\b",
    # 单个数字，如 5
    r"\b\d+\b",
    # 罗马数字
    r"\b[IVXLCDM]+\b",
]

def extract_page(text: str) -> str | None:
    for pat in PAGE_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group().replace(" ", "")
    return None

# =========================
# 文件名提取（解决正则冲突）
# =========================
def extract_filename(text: str) -> str | None:
    """
    从 OCR 文本中提取文件名
    图集号示例：24G912-1
    页码示例：5-9 / 5 / I
    """
    # 允许尾部 1 到 3 位数字（例如："12J2" 或 "24G912"），仍保持大小写敏感（只匹配大写字母）
    # 支持如 23J909, 06J908-1, L13J8, L13J5-1
    atlas_pattern = r'([A-Z]{0,2}\d{2,3}[A-Z]+\d{1,4}(?:-\d+)?)'
    atlas_match = re.search(atlas_pattern, text)

    if not atlas_match:
        return None

    atlas = atlas_match.group()

    # 移除图集号，防止页码误匹配
    rest_text = text.replace(atlas, " ")

    page = extract_page(rest_text)
    if not page:
        return None

    return f"{atlas}_{page}.pdf"

# =========================
# 单页 PDF 导出
# =========================
def export_single_page(src_pdf: str, page_index: int, out_path: str):
    src = fitz.open(src_pdf)
    dst = fitz.open()
    dst.insert_pdf(src, from_page=page_index, to_page=page_index)
    dst.save(out_path)
    dst.close()
    src.close()

# =========================
# 处理单个 PDF（一个 PDF → 一个文件夹）
# =========================
def process_pdf(pdf_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)

    print(f"📄 PDF：{os.path.basename(pdf_path)} | 页数：{len(doc)}")

    for i, page in enumerate(doc):
        print(f"➡️ 处理第 {i + 1} 页")

        # 渲染为图片
        pix = page.get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8)
        img = img.reshape(pix.height, pix.width, pix.n)

        # 裁剪左下角
        roi = crop_left_bottom(img)

        # OCR
        text = ocr_text(roi)

        # 提取文件名
        filename = extract_filename(text)
        if filename is None:
            filename = f"page_{i + 1}.pdf"
            print(f"⚠️ 未识别成功，使用默认名：{filename}")
        else:
            print(f"✅ 识别文件名：{filename}")

        out_path = os.path.join(output_dir, filename)
        export_single_page(pdf_path, i, out_path)

    doc.close()
    print(f"🎉 完成：{os.path.basename(pdf_path)}")

# =========================
# 输入调度（文件 or 文件夹）
# =========================
def process_input(input_path: str, output_root: str):
    os.makedirs(output_root, exist_ok=True)

    if os.path.isfile(input_path):
        pdf_name = os.path.splitext(os.path.basename(input_path))[0]
        out_dir = os.path.join(output_root, pdf_name)
        process_pdf(input_path, out_dir)

    elif os.path.isdir(input_path):
        for name in sorted(os.listdir(input_path)):
            if not name.lower().endswith(".pdf"):
                continue

            pdf_path = os.path.join(input_path, name)
            pdf_name = os.path.splitext(name)[0]
            out_dir = os.path.join(output_root, pdf_name)

            print("\n" + "=" * 60)
            process_pdf(pdf_path, out_dir)

    else:
        raise ValueError("输入路径不存在")

# =========================
# CLI 入口
# =========================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="拆分建筑规范 PDF，并基于左下角 OCR 自动命名（支持批量）"
    )
    parser.add_argument(
        "input",
        help="PDF 文件路径，或包含 PDF 的文件夹"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output_pages",
        help="输出根目录（默认：output_pages）"
    )

    args = parser.parse_args()
    process_input(args.input, args.output)
