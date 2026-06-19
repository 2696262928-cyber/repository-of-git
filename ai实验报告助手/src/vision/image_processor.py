"""基于 OpenCV 的图像预处理、内容分类、质量评估与内容提取模块。

所有 OpenCV 调用集中于此，对外暴露稳定的函数接口。
调用方需自行 try/except 包裹以兜底 OpenCV 不可用的情况。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

# ── 数据类 ──────────────────────────────────────────────


class ImageLabel(str, Enum):
    """图片内容类型标签。"""
    WAVEFORM = "waveform"
    CODE_SCREENSHOT = "code_screenshot"
    TABLE = "table"
    CIRCUIT_DIAGRAM = "circuit_diagram"
    PHOTO = "photo"
    TEXT_SCAN = "text_scan"
    UNKNOWN = "unknown"


@dataclass
class ImageContentType:
    """图片内容分类结果。"""
    label: ImageLabel
    confidence: float  # 0.0 ~ 1.0
    description: str   # 中文描述

    def to_message(self, index: int) -> str:
        """生成一条可供 UI 展示的中文摘要。"""
        return f"[图{index}] {self.description}（置信度 {self.confidence:.0%}）"


@dataclass
class ImageQualityResult:
    """图片质量评估结果。"""
    is_blurry: bool
    laplacian_score: float
    contrast_score: float
    warnings: list[str] = field(default_factory=list)

    def to_message(self, index: int) -> str | None:
        if self.warnings:
            return f"[图{index}] 质量警告：{'；'.join(self.warnings)}"
        return None


@dataclass
class TableContent:
    """表格图片的结构化提取结果。"""
    rows: int
    cols: int
    cells: list[list[str]]  # cells[row][col]
    raw_text: str           # 所有单元格文本按行列拼接

    def to_message(self, index: int) -> str:
        preview = self.raw_text[:200].replace("\n", " | ")
        return f"[图{index}] 表格提取：{self.rows} 行 × {self.cols} 列 — 内容预览：{preview}..."


@dataclass
class WaveformContent:
    """波形图内容分析结果。"""
    has_signal: bool        # 是否有实际波形（非空坐标系）
    curve_count: int        # 检测到的波形曲线数量
    signal_pixels: int      # 波形信号像素点数
    description: str        # 中文描述

    def to_message(self, index: int) -> str:
        if self.has_signal:
            return f"[图{index}] 检测到 {self.curve_count} 条波形曲线（信号像素 {self.signal_pixels}），确认为有效波形数据。"
        return f"[图{index}] 疑似空白坐标系/无信号截图 — 未检测到有效波形曲线，建议补充实际测量结果。"


@dataclass
class ImageAnalysisResult:
    """综合图片分析结果。"""
    content_type: ImageContentType
    quality: ImageQualityResult
    text_regions: int
    # ── 内容提取字段 ──
    table_content: TableContent | None = None
    waveform_content: WaveformContent | None = None
    extracted_text: str = ""  # 代码截图 / 文本扫描时填充


# ── 内部工具 ────────────────────────────────────────────


def _ensure_grayscale(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        import cv2
        return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    return image


def _resize_for_analysis(image: np.ndarray, max_dim: int = 1024) -> np.ndarray:
    """缩放图像以加速分析流程，避免对大图全分辨率运算。"""
    h, w = image.shape[:2]
    if max(h, w) <= max_dim:
        return image
    import cv2
    scale = max_dim / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _get_ocr_engine():
    """懒加载 RapidOCR 引擎（单例）。"""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None
    if not hasattr(_get_ocr_engine, "_instance"):
        _get_ocr_engine._instance = RapidOCR()
    return _get_ocr_engine._instance


def _ocr_region(image_array: np.ndarray) -> str:
    """对单个图像区域做 OCR，返回文本。"""
    engine = _get_ocr_engine()
    if engine is None:
        return ""
    try:
        result, _ = engine(image_array)
        if not result:
            return ""
        return " ".join(item[1] for item in result if len(item) >= 2 and item[1])
    except Exception:
        return ""


# ── OCR 预处理 ──────────────────────────────────────────


def preprocess_for_ocr(
    image: np.ndarray,
    *,
    deskew: bool = True,
    denoise_strength: int = 10,
    clahe_clip: float = 2.0,
    block_size: int = 15,
    c_value: int = 4,
) -> np.ndarray:
    """对图像做 OCR 前的预处理管线。

    Args:
        image: RGB 或灰度 numpy 数组。
        deskew: 是否执行纠偏。
        denoise_strength: 降噪强度（越大越强，建议 5~15）。
        clahe_clip: CLAHE 对比度剪辑限幅。
        block_size: 自适应阈值块大小（必须为奇数）。
        c_value: 自适应阈值常数偏移。

    Returns:
        二值化后的 numpy 数组（uint8），可直接送入 OCR 引擎。
    """
    import cv2

    gray = _ensure_grayscale(image)
    if deskew:
        gray = _deskew_image(gray)

    # CLAHE 自适应直方图均衡 — 增强局部对比度
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # 降噪
    denoised = cv2.fastNlMeansDenoising(enhanced, None, denoise_strength, 7, 21)

    # 自适应阈值二值化 — 将文字从背景中分离
    if block_size % 2 == 0:
        block_size += 1
    binary = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c_value,
    )

    return binary


def _deskew_image(gray: np.ndarray) -> np.ndarray:
    """基于 HoughLinesP 检测文本行主导角度并旋转校正。"""
    import cv2

    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 8,
    )
    lines = cv2.HoughLinesP(
        binary, 1, np.pi / 180, threshold=100, minLineLength=50, maxLineGap=10,
    )
    if lines is None or len(lines) < 3:
        return gray  # 直线太少，跳过纠偏

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if -45 < angle < 45:
            angles.append(angle)

    if not angles:
        return gray

    median_angle = np.median(angles)
    if abs(median_angle) < 0.5:
        return gray  # 角度极小，无需旋转

    h, w = gray.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(
        gray, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated


# 公开别名（保持旧名称兼容）
deskew_image = _deskew_image


# ── 文本区域检测 ────────────────────────────────────────


def detect_text_regions(
    image: np.ndarray,
    *,
    min_area: int = 500,
    max_area_ratio: float = 0.8,
) -> list[tuple[int, int, int, int]]:
    """通过形态学操作 + 轮廓检测定位可能的文字区域。

    Returns:
        [(x, y, w, h), ...] 矩形区域列表，按 y 坐标从上到下排序。
    """
    import cv2

    gray = _ensure_grayscale(image)
    h, w = gray.shape[:2]
    max_area = int(w * h * max_area_ratio)

    # 二值化（反转：文字为白）
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 6,
    )

    # 形态学膨胀 — 将相邻字符连成文本行
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
    dilated = cv2.dilate(binary, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for contour in contours:
        x, y, cw, ch = cv2.boundingRect(contour)
        area = cw * ch
        if min_area <= area <= max_area:
            # 适当扩展边距
            pad_x = int(cw * 0.05)
            pad_y = int(ch * 0.1)
            regions.append((
                max(0, x - pad_x),
                max(0, y - pad_y),
                min(w - 1, x + cw + pad_x) - max(0, x - pad_x),
                min(h - 1, y + ch + pad_y) - max(0, y - pad_y),
            ))

    # 按 y 坐标排序
    regions.sort(key=lambda r: r[1])
    return _merge_overlapping_regions(regions)


def _merge_overlapping_regions(
    regions: list[tuple[int, int, int, int]],
) -> list[tuple[int, int, int, int]]:
    """合并重叠的文本区域。"""
    if len(regions) <= 1:
        return regions

    merged = []
    current = list(regions[0])
    for rx, ry, rw, rh in regions[1:]:
        cx, cy, cw, ch = current
        # 水平方向重叠且垂直方向接近
        if (rx < cx + cw and rx + rw > cx) and abs(ry - cy) < 20:
            current[0] = min(cx, rx)
            current[1] = min(cy, ry)
            current[2] = max(cx + cw, rx + rw) - current[0]
            current[3] = max(cy + ch, ry + rh) - current[1]
        else:
            merged.append(tuple(current))
            current = [rx, ry, rw, rh]
    merged.append(tuple(current))
    return merged


# ── 图片内容分类 ────────────────────────────────────────


def classify_image_content(image: np.ndarray) -> ImageContentType:
    """判断图片的内容类型。

    基于边缘、直线和轮廓特征进行启发式分类。
    """
    import cv2

    small = _resize_for_analysis(image, 1024)
    gray = _ensure_grayscale(small)
    h, w = gray.shape[:2]

    # Canny 边缘检测
    edges = cv2.Canny(gray, 50, 150)

    # HoughLinesP 直线检测
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=80, minLineLength=30, maxLineGap=10,
    )
    line_count = len(lines) if lines is not None else 0

    # 轮廓
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour_count = len(contours)

    # 计算水平线与竖直线数量
    horizontal_lines = 0
    vertical_lines = 0
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < 10 or angle > 170:
                horizontal_lines += 1
            elif 80 < angle < 100:
                vertical_lines += 1

    # 边缘密度
    edge_density = np.sum(edges > 0) / (h * w)

    # 均匀度 — 将图像分为网格，统计每个格子内的边缘数量方差
    grid_size = 8
    cell_h, cell_w = h // grid_size, w // grid_size
    cell_densities = []
    for row in range(grid_size):
        for col in range(grid_size):
            cell = edges[row * cell_h:(row + 1) * cell_h, col * cell_w:(col + 1) * cell_w]
            cell_densities.append(np.sum(cell > 0) / (cell_h * cell_w))
    uniformity = 1.0 - float(np.std(cell_densities) / (np.mean(cell_densities) + 1e-6))
    uniformity = max(0.0, min(1.0, uniformity))

    # ── 分类判定 ──
    # 表格：大量水平+垂直线且正交
    if line_count > 20 and horizontal_lines > 8 and vertical_lines > 8:
        ratio = min(horizontal_lines, vertical_lines) / max(horizontal_lines, vertical_lines, 1)
        if ratio > 0.3:
            confidence = min(0.9, 0.5 + ratio)
            return ImageContentType(
                ImageLabel.TABLE, confidence,
                "疑似表格 — 检测到规则网格线与行列结构，建议提取为结构化数据",
            )

    # 波形图/时序图：大量水平线但很少竖直线，且边缘密度中等
    if horizontal_lines > 15 and vertical_lines < horizontal_lines * 0.3 and 0.03 < edge_density < 0.25:
        confidence = min(0.85, 0.4 + horizontal_lines / 60)
        return ImageContentType(
            ImageLabel.WAVEFORM, confidence,
            "疑似波形图/时序图 — 检测到大量水平扫描线与锯齿边缘，建议用文字补充关键参数（周期、占空比、幅值）",
        )

    # 代码截图：密集小轮廓、低均匀度、少量长直线
    if contour_count > 150 and edge_density > 0.05 and line_count < 10:
        confidence = min(0.85, 0.3 + contour_count / 500)
        return ImageContentType(
            ImageLabel.CODE_SCREENSHOT, confidence,
            "疑似代码/文本截图 — 检测到密集字符级边缘，代码应以文字形式提交，截图中的代码无法被检测系统分析",
        )

    # 电路图/框图：中等数量线段 + 中低边缘密度 + 不规则轮廓
    if 5 < line_count <= 40 and 0.02 < edge_density < 0.15 and uniformity < 0.7:
        confidence = min(0.8, 0.3 + line_count / 80)
        return ImageContentType(
            ImageLabel.CIRCUIT_DIAGRAM, confidence,
            "疑似电路图/框图/流程图 — 检测到不规则连线与节点结构，建议补充文字描述关键电路参数与原理",
        )

    # 纯文本扫描：较均匀的中等边缘密度 + 较多文本区域
    text_regions = detect_text_regions(small)
    if len(text_regions) >= 3 and uniformity > 0.5:
        return ImageContentType(
            ImageLabel.TEXT_SCAN, 0.7,
            "纯文本扫描/文档页 — 建议通过 OCR 提取文字内容",
        )

    # 默认
    return ImageContentType(
        ImageLabel.PHOTO if edge_density < 0.05 else ImageLabel.UNKNOWN,
        0.3,
        "普通照片或无法识别的图像类型",
    )


# ── 图像质量评估 ─────────────────────────────────────────


def assess_image_quality(
    image: np.ndarray,
    *,
    blur_threshold: float = 100.0,
    contrast_min: float = 30.0,
) -> ImageQualityResult:
    """评估图像质量（模糊度与对比度）。

    Args:
        image: RGB 或灰度 numpy 数组。
        blur_threshold: Laplacian 方差低于此值视为模糊。
        contrast_min: 标准差低于此值视为低对比度。

    Returns:
        ImageQualityResult 含模糊检测、Laplacian 分数、对比度分数和中文警告列表。
    """
    import cv2

    gray = _ensure_grayscale(image)

    # Laplacian 方差 — 检测模糊
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    laplacian_score = float(laplacian.var())

    # 标准差 — 检测对比度
    contrast_score = float(np.std(gray))

    is_blurry = laplacian_score < blur_threshold
    low_contrast = contrast_score < contrast_min

    warnings = []
    if laplacian_score < blur_threshold * 0.5:
        warnings.append("图像严重模糊，OCR 准确率将大幅下降")
    elif is_blurry:
        warnings.append("图像轻微模糊，可能影响 OCR 准确率")
    if low_contrast:
        warnings.append("图像对比度偏低，文字可能难以辨认")

    return ImageQualityResult(
        is_blurry=is_blurry,
        laplacian_score=round(laplacian_score, 1),
        contrast_score=round(contrast_score, 1),
        warnings=warnings,
    )


# ── 内容提取：表格 ──────────────────────────────────────


def extract_table_content(image: np.ndarray) -> TableContent:
    """从表格图片中检测行列结构并做全图 OCR。

    不再逐格 OCR（太慢），改为一次全图 OCR + 网格行列检测。
    """
    import cv2

    gray = _ensure_grayscale(image)
    h, w = gray.shape[:2]

    # 二值化
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 6,
    )

    # 检测水平线和竖直线
    h_lines_raw = cv2.HoughLinesP(
        binary, 1, np.pi / 180, threshold=100, minLineLength=int(w * 0.3), maxLineGap=15,
    )
    v_lines_raw = cv2.HoughLinesP(
        binary, 1, np.pi / 180, threshold=100, minLineLength=int(h * 0.3), maxLineGap=15,
    )

    h_positions = []
    if h_lines_raw is not None:
        for line in h_lines_raw:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < 8 or angle > 172:
                h_positions.append((y1 + y2) // 2)

    v_positions = []
    if v_lines_raw is not None:
        for line in v_lines_raw:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if 82 < angle < 98:
                v_positions.append((x1 + x2) // 2)

    h_sorted = sorted(set(_cluster_values(h_positions, gap=10)))
    v_sorted = sorted(set(_cluster_values(v_positions, gap=10)))

    rows = len(h_sorted) - 1 if len(h_sorted) >= 2 else 0
    cols = len(v_sorted) - 1 if len(v_sorted) >= 2 else 0

    # 全图 OCR（一次调用，快）
    full_text = _ocr_region(gray).strip()

    return TableContent(rows=rows, cols=cols, cells=[], raw_text=full_text)


def _cluster_values(values: list[int], gap: int = 10) -> list[int]:
    """将相近的数值聚类取均值。"""
    if not values:
        return []
    sorted_vals = sorted(values)
    clusters: list[list[int]] = [[sorted_vals[0]]]
    for v in sorted_vals[1:]:
        if v - clusters[-1][-1] <= gap:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [int(np.mean(c)) for c in clusters]


# ── 内容提取：波形图 ────────────────────────────────────


def extract_waveform_data(
    image: np.ndarray,
    *,
    min_signal_pixels: int = 200,
) -> WaveformContent:
    """分析波形图是否包含实际波形信号。

    流程：Canny 边缘 → findContours → 过滤水平/垂直直线 →
          保留锯齿/曲线轮廓 → 统计信号点。

    Args:
        image: RGB 或灰度 numpy 数组。
        min_signal_pixels: 波形信号像素数低于此值视为无信号。

    Returns:
        WaveformContent 含是否有信号、曲线数量和信号像素数。
    """
    import cv2

    gray = _ensure_grayscale(image)
    h, w = gray.shape[:2]

    # Canny 边缘检测
    edges = cv2.Canny(gray, 40, 120)

    # 查找轮廓
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    curve_contours = []
    total_signal_pixels = 0
    for contour in contours:
        if len(contour) < 20:
            continue  # 太小的忽略

        # 近似多边形
        epsilon = 0.01 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # 用最小外接矩形判断是否接近水平/竖直线
        rect = cv2.minAreaRect(contour)
        (rw, rh) = rect[1]
        if min(rw, rh) < 2:
            continue
        aspect_ratio = max(rw, rh) / min(rw, rh)

        # 如果近似后只有 2~4 个顶点且宽高比极端 → 直线（网格线），排除
        if len(approx) <= 4 and aspect_ratio > 8:
            continue

        # 保留曲线轮廓
        curve_contours.append(contour)
        total_signal_pixels += len(contour)

    has_signal = total_signal_pixels >= min_signal_pixels
    curve_count = len(curve_contours)

    if has_signal:
        desc = f"检测到 {curve_count} 条波形曲线（信号像素 {total_signal_pixels}），确认为有效波形数据。"
    else:
        desc = "疑似空白坐标系/无信号截图 — 未检测到有效波形曲线，建议补充实际测量结果。"

    return WaveformContent(
        has_signal=has_signal,
        curve_count=curve_count,
        signal_pixels=total_signal_pixels,
        description=desc,
    )


# ── 内容提取：代码截图 ───────────────────────────────────


def extract_code_screenshot_text(image: np.ndarray) -> str:
    """从代码截图/文本扫描图片中逐行 OCR 提取文本。

    流程：detect_text_regions 定位文本行 → 按 y 排序 → 逐行 OCR → 拼接。

    Returns:
        提取的文本字符串，保留行结构。
    """
    try:
        regions = detect_text_regions(image)
    except Exception:
        return ""

    if not regions:
        # 回退：全图 OCR
        return _ocr_region(image)

    lines: list[str] = []
    for rx, ry, rw, rh in regions:
        crop = image[ry:ry + rh, rx:rx + rw]
        if crop.size == 0:
            continue
        text = _ocr_region(crop).strip()
        if text:
            # 按缩进粗略还原：左侧 x 坐标越大 → 缩进越多
            indent_level = max(0, rx // 30)
            lines.append(" " * indent_level + text)

    return "\n".join(lines)


# ── 综合分析入口 ────────────────────────────────────────


def analyze_image(
    image: np.ndarray,
    *,
    blur_threshold: float = 100.0,
    extract_content: bool = False,
) -> ImageAnalysisResult:
    """对单张图像执行完整分析：分类 → 质量评估 → 内容提取。

    根据分类结果自动触发对应的内容提取：
    - 表格 → extract_table_content()
    - 波形图 → extract_waveform_data()
    - 代码截图/文本扫描 → extract_code_screenshot_text()

    Args:
        image: RGB 或灰度 numpy 数组。
        blur_threshold: 模糊检测阈值。
        extract_content: 是否执行昂贵的内容提取（表格 OCR/波形分析/代码 OCR）。
                         默认 False，仅做分类和质量检测，保证首次渲染速度。
    """
    content_type = classify_image_content(image)
    quality = assess_image_quality(image, blur_threshold=blur_threshold)

    try:
        regions = detect_text_regions(image)
    except Exception:
        regions = []

    # 根据分类触发内容提取（仅在 extract_content=True 时）
    table_content = None
    waveform_content = None
    extracted_text = ""

    if extract_content:
        label = content_type.label
        try:
            if label == ImageLabel.TABLE:
                table_content = extract_table_content(image)
            elif label == ImageLabel.WAVEFORM:
                waveform_content = extract_waveform_data(image)
            elif label in (ImageLabel.CODE_SCREENSHOT, ImageLabel.TEXT_SCAN):
                extracted_text = extract_code_screenshot_text(image)
        except Exception:
            pass  # 内容提取失败不影响整体分析结果

    return ImageAnalysisResult(
        content_type=content_type,
        quality=quality,
        text_regions=len(regions),
        table_content=table_content,
        waveform_content=waveform_content,
        extracted_text=extracted_text,
    )


# ── 批量处理工具 ────────────────────────────────────────


def analyze_images_from_bytes(
    image_bytes_list: list[bytes],
    *,
    blur_threshold: float = 100.0,
    extract_content: bool = False,
) -> tuple[list[ImageAnalysisResult], int]:
    """将 bytes 列表解码为图像并逐一分析。

    用于处理从 PDF/DOCX 提取出的图片数据。

    Returns:
        (results, extracted_count): 分析结果列表 + 实际做了内容提取的图片数。
    """
    from io import BytesIO

    from PIL import Image

    # 预初始化 OCR 引擎（避免首次调用时卡顿）
    if extract_content:
        _get_ocr_engine()

    results: list[ImageAnalysisResult] = []
    extracted_count = 0
    for img_bytes in image_bytes_list:
        try:
            pil_image = Image.open(BytesIO(img_bytes)).convert("RGB")
            image_array = np.array(pil_image)
            result = analyze_image(image_array, blur_threshold=blur_threshold, extract_content=extract_content)
            if extract_content and (result.table_content is not None or result.waveform_content is not None or result.extracted_text):
                extracted_count += 1
        except Exception:
            result = ImageAnalysisResult(
                content_type=ImageContentType(ImageLabel.UNKNOWN, 0.0, "图片解码失败，无法分析"),
                quality=ImageQualityResult(is_blurry=False, laplacian_score=0.0, contrast_score=0.0),
                text_regions=0,
            )
        results.append(result)
    return results, extracted_count
