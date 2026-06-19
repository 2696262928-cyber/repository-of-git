from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import fitz
import numpy as np
from PIL import Image


@dataclass
class OCRResult:
    text: str
    page_count: int
    image_count: int
    warnings: list[str]


# ── Vision 配置加载 ─────────────────────────────────────


def _load_vision_settings() -> dict:
    """从 config/settings.json 读取 vision 配置段，失败时返回安全默认值。"""
    try:
        settings_path = Path(__file__).resolve().parent.parent.parent / "config" / "settings.json"
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data.get("vision", {})
    except Exception:
        pass
    return {}


# ── 主入口 ──────────────────────────────────────────────


def extract_visual_text(file_type: str, content: bytes, max_pages: int = 5, languages: str = "ch") -> OCRResult:
    """Extract text from PDF pages or DOCX embedded images with a pip-installable OCR backend."""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return OCRResult("", 0, 0, ["未安装 rapidocr-onnxruntime，无法进行图片 OCR。请运行 pip install -r requirements.txt。"])

    ocr_engine = RapidOCR()

    if file_type == "pdf":
        return _ocr_pdf_pages(content, ocr_engine, max_pages)
    if file_type == "docx":
        return _ocr_docx_images(content, ocr_engine)
    return OCRResult("", 0, 0, ["当前 OCR 仅支持 PDF 页面和 DOCX 内嵌图片。"])


# ── 内部实现 ────────────────────────────────────────────


def _ocr_pdf_pages(content: bytes, ocr_engine, max_pages: int) -> OCRResult:
    texts = []
    warnings = []
    pages_done = 0
    image_count = 0
    matrix = fitz.Matrix(2, 2)
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            image_count = sum(len(page.get_images(full=True)) for page in document)
            for index, page in enumerate(document[:max_pages], start=1):
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.open(BytesIO(pixmap.tobytes("png")))
                text = _safe_image_to_string(image, ocr_engine, warnings, f"第 {index} 页")
                if text.strip():
                    texts.append(f"[PDF 第 {index} 页 OCR]\n{text.strip()}")
                pages_done += 1
    except Exception as exc:
        warnings.append(f"PDF OCR 失败：{exc}")
    return OCRResult("\n\n".join(texts), pages_done, image_count, warnings)


def _ocr_docx_images(content: bytes, ocr_engine) -> OCRResult:
    texts = []
    warnings = []
    image_count = 0
    try:
        with ZipFile(BytesIO(content)) as archive:
            image_names = [
                name
                for name in archive.namelist()
                if name.startswith("word/media/") and name.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"))
            ]
            image_count = len(image_names)
            for index, name in enumerate(image_names, start=1):
                image = Image.open(BytesIO(archive.read(name)))
                text = _safe_image_to_string(image, ocr_engine, warnings, f"DOCX 图片 {index}")
                if text.strip():
                    texts.append(f"[DOCX 图片 {index} OCR]\n{text.strip()}")
    except Exception as exc:
        warnings.append(f"DOCX 图片 OCR 失败：{exc}")
    return OCRResult("\n\n".join(texts), 0, image_count, warnings)


def _safe_image_to_string(image: Image.Image, ocr_engine, warnings: list[str], label: str) -> str:
    """对图像执行 OCR，可选 OpenCV 预处理管线。

    当 vision.ocr_preprocessing 开启时，先做预处理再 OCR；
    OpenCV 不可用或预处理失败时自动回退到原始行为。
    """
    vision_settings = _load_vision_settings()
    use_preprocessing = vision_settings.get("ocr_preprocessing", True)
    use_deskew = vision_settings.get("deskew_enabled", True)

    try:
        image_array = np.array(image.convert("RGB"))

        # ── OpenCV 预处理管线 ──
        if use_preprocessing:
            try:
                from src.vision.image_processor import preprocess_for_ocr, detect_text_regions

                # 预处理（灰度 → CLAHE → 降噪 → 二值化 → 纠偏）
                processed = preprocess_for_ocr(image_array, deskew=use_deskew)

                # 尝试按文本区域分别 OCR
                try:
                    regions = detect_text_regions(image_array)
                except Exception:
                    regions = []

                if regions and len(regions) >= 1:
                    # 逐区域 OCR 并合并
                    region_texts = []
                    for rx, ry, rw, rh in regions:
                        region_crop = processed[ry:ry + rh, rx:rx + rw]
                        if region_crop.size == 0:
                            continue
                        result, _ = ocr_engine(region_crop)
                        if result:
                            region_texts.append(
                                "\n".join(item[1] for item in result if len(item) >= 2 and item[1])
                            )
                    if region_texts:
                        return "\n".join(region_texts)

                # 回退：整张预处理图做 OCR
                result, _ = ocr_engine(processed)
                if not result:
                    return ""
                return "\n".join(item[1] for item in result if len(item) >= 2 and item[1])

            except ImportError:
                warnings.append(f"{label}：OpenCV 未安装，回退到原始 OCR（可运行 pip install opencv-python-headless）")
            except Exception as exc:
                warnings.append(f"{label} OpenCV 预处理失败（{exc}），回退到原始 OCR")

        # ── 原始 OCR（无预处理） ──
        result, _ = ocr_engine(image_array)
        if not result:
            return ""
        return "\n".join(item[1] for item in result if len(item) >= 2 and item[1])

    except Exception as exc:
        warnings.append(f"{label} OCR 处理失败：{exc}")
    return ""
