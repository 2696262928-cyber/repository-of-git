from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from io import BytesIO


SECTION_KEYWORDS = {
    "实验目的": ["实验目的", "objective", "objectives"],
    "实验要求": ["实验要求", "requirements", "requirement"],
    "实验环境": ["实验环境", "environment", "configuration", "cubemx", "keil", "vscode"],
    "实验原理": ["实验原理", "principle", "overview", "background", "theory"],
    "实验过程": ["实验步骤", "实验过程", "process", "procedure", "step", "experimental content"],
    "核心代码": ["核心代码", "source code", "code modification", "main.c", "代码"],
    "运行结果": ["运行结果", "实验结果", "results", "result", "testing", "test procedure"],
    "结果分析": ["结果分析", "analysis", "timing diagram", "waveform", "现象分析"],
    "实验总结": ["实验总结", "conclusion", "summary"],
    "参考资料": ["参考资料", "references", "reference"],
}

TECHNICAL_MARKERS = {
    "嵌入式外设": ["uart", "spi", "dma", "adc", "pwm", "timer", "gpio", "oled", "w25q128", "flash"],
    "代码与配置": ["main.c", "cube", "cubemx", "hal_", "callback", "interrupt", "prescaler", "period"],
    "测试验证": ["test", "testing", "result", "press", "send", "receive", "display", "oled"],
    "定量参数": ["0x", "hz", "ms", "v", "pwm", "duty", "period", "baud", "adc"],
}


@dataclass
class ReportDiagnostics:
    text_length: int
    page_count: int
    image_count: int
    code_block_count: int
    table_count: int
    detected_sections: list[str]
    missing_sections: list[str]
    technical_markers: dict[str, int]
    format_findings: list[str]
    image_findings: list[str]
    precheck_score: int
    precheck_notes: list[str]
    extracted_image_text: str = ""  # 从图片 OCR/表格/代码截图中提取的文本


# ── Vision 配置加载 ─────────────────────────────────────


def _load_vision_settings() -> dict:
    """从 config/settings.json 读取 vision 配置段。"""
    try:
        settings_path = Path(__file__).resolve().parent.parent.parent / "config" / "settings.json"
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data.get("vision", {})
    except Exception:
        pass
    return {}


# ── 主分析入口 ──────────────────────────────────────────


def analyze_report_quality(
    parsed_report,
    image_bytes_list: list[bytes] | None = None,
    extract_content: bool = False,
) -> dict:
    """分析实验报告的结构与质量。

    Args:
        parsed_report: ParsedReport 数据类实例。
        image_bytes_list: 可选，从文档中提取的图片 bytes 列表，用于视觉分析。
        extract_content: 是否执行昂贵的内容提取（表格 OCR/波形信号检测）。
                         默认 False，仅做分类和质量检测。

    Returns:
        dict — ReportDiagnostics 的字典表示。
    """
    text = parsed_report.full_text
    lowered = text.lower()

    detected_sections = []
    missing_sections = []
    for section, keywords in SECTION_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            detected_sections.append(section)
        else:
            missing_sections.append(section)

    marker_counts = {
        group: sum(lowered.count(keyword.lower()) for keyword in keywords)
        for group, keywords in TECHNICAL_MARKERS.items()
    }
    notes = []
    format_findings = []
    image_findings = []
    score = 100

    if parsed_report.page_count:
        format_findings.append(f"检测到页数：{parsed_report.page_count} 页。")
    table_count = len(parsed_report.tables)
    code_block_count = len(parsed_report.code_blocks)
    if table_count:
        format_findings.append(f"检测到表格：{table_count} 个。")
    if detected_sections:
        format_findings.append("检测到章节结构：" + "、".join(detected_sections) + "。")
    if missing_sections:
        format_findings.append("可能缺失章节：" + "、".join(missing_sections) + "。")

    # ── 图片分析 ──
    vision_settings = _load_vision_settings()
    extracted_image_text = ""
    if vision_settings.get("image_analysis_enabled", True) and image_bytes_list:
        extracted_image_text = _analyze_images(
            image_bytes_list, image_findings, vision_settings, score, notes,
            extract_content=extract_content,
        )
    else:
        _fallback_image_findings(parsed_report, image_findings)

    if len(text) < 1200:
        score -= 18
        notes.append("正文长度偏短，可能缺少充分的过程描述或结果分析。")
    if "运行结果" not in detected_sections and "结果分析" not in detected_sections:
        score -= 14
        notes.append("未明显识别到运行结果或结果分析。")
    if "核心代码" not in detected_sections:
        score -= 12
        notes.append("未明显识别到核心代码或代码修改说明。")
    if "实验总结" not in detected_sections:
        score -= 6
        notes.append("未明显识别到实验总结。")
    if "参考资料" not in detected_sections:
        score -= 4
        notes.append("未明显识别到参考资料。")
    if parsed_report.file_type == "pdf" and len(text) < 100:
        score -= 30
        notes.append("PDF 文本提取结果过少，可能是扫描版，需要 OCR。")
    if parsed_report.image_count == 0 and parsed_report.file_type in {"pdf", "docx"}:
        score -= 4
        notes.append("未检测到图片对象；若报告依赖截图，需要确认原文是否包含结果截图。")

    diagnostics = ReportDiagnostics(
        text_length=len(text),
        page_count=parsed_report.page_count,
        image_count=parsed_report.image_count,
        code_block_count=code_block_count,
        table_count=table_count,
        detected_sections=detected_sections,
        missing_sections=missing_sections,
        technical_markers=marker_counts,
        format_findings=format_findings,
        image_findings=image_findings,
        precheck_score=max(0, min(100, score)),
        precheck_notes=notes,
        extracted_image_text=extracted_image_text,
    )
    return asdict(diagnostics)


# ── 图片分析 ────────────────────────────────────────────


def _analyze_images(
    image_bytes_list: list[bytes],
    image_findings: list[str],
    vision_settings: dict,
    score: int,
    notes: list[str],
    extract_content: bool = False,
) -> str:
    """使用 OpenCV 对图片进行内容分类、质量评估与内容提取，将结果写入 image_findings。

    Args:
        extract_content: 是否执行昂贵的内容提取（表格 OCR/波形分析/代码 OCR）。
                         默认 False，仅做分类和质量检测。

    Returns:
        str — 从代码截图/文本扫描中提取的文本，可供合并到报告正文。
    """
    image_findings.append(f"检测到图片对象：{len(image_bytes_list)} 个。")
    accumulated_text = ""

    try:
        from src.vision.image_processor import (
            ImageLabel,
            analyze_images_from_bytes,
        )

        quality_threshold = vision_settings.get("quality_threshold", 100.0)
        results, extracted_count = analyze_images_from_bytes(
            image_bytes_list,
            blur_threshold=quality_threshold,
            extract_content=extract_content,
        )
        if extract_content and extracted_count > 0:
            image_findings.append(f"已完成 {extracted_count}/{len(image_bytes_list)} 张图片的内容提取。")

        # 统计各类型数量
        type_counts: dict[ImageLabel, int] = {}
        for r in results:
            type_counts[r.content_type.label] = type_counts.get(r.content_type.label, 0) + 1

        # 汇总行
        summary_parts = []
        label_names = {
            ImageLabel.WAVEFORM: "波形图",
            ImageLabel.CODE_SCREENSHOT: "代码截图",
            ImageLabel.TABLE: "表格",
            ImageLabel.CIRCUIT_DIAGRAM: "电路图",
            ImageLabel.PHOTO: "照片",
            ImageLabel.TEXT_SCAN: "文本扫描",
            ImageLabel.UNKNOWN: "未知类型",
        }
        for label, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            summary_parts.append(f"{label_names.get(label, label.value)}×{count}")
        if summary_parts:
            image_findings.append("图片类型： " + "，".join(summary_parts) + "。")

        # 逐张分析
        code_screenshot_count = 0
        blurry_count = 0
        empty_waveform_count = 0
        for index, result in enumerate(results, start=1):
            # 内容分类信息
            msg = result.content_type.to_message(index)
            image_findings.append(msg)

            # ── 表格内容提取 ──
            if result.table_content is not None:
                tc = result.table_content
                if tc.rows > 0 and tc.cols > 0:
                    image_findings.append(tc.to_message(index))
                    if tc.raw_text:
                        accumulated_text += f"\n\n[图{index} 表格提取]\n{tc.raw_text}"

            # ── 波形信号检测 ──
            if result.waveform_content is not None:
                wc = result.waveform_content
                image_findings.append(wc.to_message(index))
                if not wc.has_signal:
                    empty_waveform_count += 1

            # ── 代码截图文本提取 ──
            if result.extracted_text:
                accumulated_text += f"\n\n[图{index} 代码/文本提取]\n{result.extracted_text}"

            # 质量警告
            qmsg = result.quality.to_message(index)
            if qmsg:
                image_findings.append(qmsg)

            # 统计需要关注的问题
            if result.content_type.label == ImageLabel.CODE_SCREENSHOT:
                code_screenshot_count += 1
            if result.quality.is_blurry:
                blurry_count += 1

        # 根据图片分析调整预检评分
        if code_screenshot_count > 0:
            penalty = min(12, code_screenshot_count * 4)
            score -= penalty
            notes.append(f"检测到 {code_screenshot_count} 张代码/文本截图 — "
                         "代码应以文字形式提交，截图中的代码无法被分析。建议补充文字版代码。")

        if blurry_count > 0:
            penalty = min(8, blurry_count * 2)
            score -= penalty
            notes.append(f"检测到 {blurry_count} 张图片质量偏低（模糊/低对比度），"
                         "可能影响 OCR 准确率，建议重新上传清晰图片。")

        # 建议补充文字说明
        waveform_count = type_counts.get(ImageLabel.WAVEFORM, 0)
        circuit_count = type_counts.get(ImageLabel.CIRCUIT_DIAGRAM, 0)
        if waveform_count > 0:
            notes.append(f"检测到 {waveform_count} 张波形图 — 建议在正文中用文字描述关键波形参数"
                         "（周期、频率、占空比、幅值等）。")
        if empty_waveform_count > 0:
            notes.append(f"其中 {empty_waveform_count} 张波形图疑似空白坐标系/无信号数据 — "
                         "请确认是否误放截图或补充实际测量波形。")
        if circuit_count > 0:
            notes.append(f"检测到 {circuit_count} 张电路图/框图 — 建议在正文中说明电路结构与工作原理。")

    except ImportError:
        image_findings.append("OpenCV 未安装，无法进行图片内容分析。"
                              "（可运行 pip install opencv-python-headless）")
    except Exception as exc:
        image_findings.append(f"图片分析失败：{exc}，已回退到基础统计。")

    return accumulated_text


def _fallback_image_findings(parsed_report, image_findings: list[str]) -> None:
    """当未启用图片分析时的回退提示。"""
    if parsed_report.image_count > 0:
        image_findings.append(f"检测到图片对象：{parsed_report.image_count} 个。")
        image_findings.append("当前版本只统计图片数量并提供页面预览，不会识别图片中的文字、波形、截图内容或实验现象。")
        image_findings.append("若实验结果主要体现在截图中，建议报告正文配套写出关键结果说明，便于模型评阅。")
    elif parsed_report.file_type in {"pdf", "docx"}:
        image_findings.append("未检测到图片对象；如果原报告包含截图，可能是以背景/矢量/扫描页面形式存在。")
