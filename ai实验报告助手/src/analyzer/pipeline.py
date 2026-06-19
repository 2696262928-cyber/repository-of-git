"""并行分析流水线 — 文本+图片同步分析，进度可视化。

使用 ThreadPoolExecutor 并行执行文本凝练和图片分析，
通过 progress_callback 回调实时报告进度。
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
from typing import Callable

from src.analyzer.text_condenser import CondensationResult, condense_report_text, extract_key_parameters
from src.evaluator.report_analyzer import analyze_report_quality
from src.parser.document_parser import (
    ImageContext,
    ParsedReport,
    extract_document_images_with_context,
    parse_uploaded_file,
)
from src.vision.image_processor import ImageAnalysisResult, ImageLabel, analyze_images_from_bytes


@dataclass
class PipelineProgress:
    """流水线进度状态。"""
    step_name: str       # 当前步骤名
    step_index: int      # 当前步骤 (1-based)
    total_steps: int     # 总步骤数
    detail: str = ""     # 详细信息
    percent: float = 0.0  # 当前步骤完成百分比


@dataclass
class PipelineResult:
    """流水线完整分析结果。"""
    parsed: ParsedReport
    condensation: CondensationResult
    key_parameters: dict[str, list[str]]
    image_contexts: list[ImageContext]
    image_results: list[ImageAnalysisResult]
    diagnostics: dict
    merged_findings: list[str]
    merged_report: str

    # 统计
    total_images: int = 0
    waveform_images: int = 0
    table_images: int = 0
    code_screenshot_images: int = 0
    blurry_images: int = 0
    empty_waveform_images: int = 0


def run_analysis_pipeline(
    uploaded_file,
    *,
    use_content_extraction: bool = False,
    progress_callback: Callable[[PipelineProgress], None] | None = None,
) -> PipelineResult:
    """执行完整分析流水线：文档解析 → 并行(文本凝练 + 图片分析) → 融合。

    Args:
        uploaded_file: Streamlit UploadedFile 对象。
        use_content_extraction: 是否执行昂贵的图片内容提取（表格 OCR 等）。
        progress_callback: 进度回调，用于 UI 实时更新。

    Returns:
        PipelineResult 含所有分析结果。
    """
    total_steps = 6 if use_content_extraction else 5

    def report(step_index: int, step_name: str, detail: str = "", percent: float = 0.0):
        if progress_callback:
            progress_callback(PipelineProgress(
                step_name=step_name,
                step_index=step_index,
                total_steps=total_steps,
                detail=detail,
                percent=percent,
            ))

    # ── Step 1: 文档解析 ──
    report(1, "文档解析", "正在解析 PDF/DOCX 文档结构...")
    parsed = parse_uploaded_file(uploaded_file)
    report(1, "文档解析", f"解析完成 — {parsed.page_count} 页, {parsed.image_count} 张图片", 1.0)

    # ── Step 2: 并行 — 文本凝练 + 图片提取分析 ──
    report(2, "文本凝练 & 图片分析", "正在并行执行文本凝练和图片提取分类...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # 文本凝练任务
        text_future = executor.submit(
            condense_report_text, parsed.full_text, 6000,
        )

        # 图片提取+分析任务
        def _extract_and_analyze():
            contexts = extract_document_images_with_context(uploaded_file)
            img_bytes_list = [c.image_bytes for c in contexts]
            if img_bytes_list:
                img_results, extracted = analyze_images_from_bytes(
                    img_bytes_list, extract_content=use_content_extraction,
                )
            else:
                img_results, extracted = [], 0
            return contexts, img_results, extracted

        image_future = executor.submit(_extract_and_analyze)

        # 等待两个任务完成
        condensation: CondensationResult = text_future.result()
        contexts, img_results, extracted_count = image_future.result()

    report(2, "文本凝练 & 图片分析",
           f"文本 {condensation.original_length}→{condensation.condensed_length} 字符, "
           f"图片 {len(img_results)} 张（提取 {extracted_count} 张内容）",
           1.0)

    # ── Step 3: 关键词提取（基于原文本） ──
    report(3, "关键词提取", "正在提取技术参数和关键信息...")
    key_params = extract_key_parameters(parsed.full_text)
    param_count = sum(len(v) for v in key_params.values())
    report(3, "关键词提取", f"提取到 {param_count} 个技术参数，{len(key_params)} 个类别", 1.0)

    # ── Step 4: 图片上下文关联 ──
    report(4, "图片-文本位置关联", f"正在关联 {len(contexts)} 张图片与原文位置...")
    if contexts and img_results:
        _enrich_image_findings_with_context(img_results, contexts)

        # 统计
        stats = _count_image_types(img_results)
        detail_parts = [f"{k}: {v}张" for k, v in stats.items() if v > 0]
        report(4, "图片-文本位置关联", "关联完成 — " + ", ".join(detail_parts), 1.0)
    else:
        report(4, "图片-文本位置关联", "无图片可关联", 1.0)

    # ── Step 5: 综合融合 ──
    report(5, "综合分析融合", "正在生成文本+图片融合分析报告...")
    from src.analyzer.result_merger import merge_text_image_analysis

    merged = merge_text_image_analysis(
        condensation.condensed_text,
        key_params,
        img_results,
        contexts,
    )
    report(5, "综合分析融合", "融合报告生成完成", 1.0)

    # ── Step 6 (可选): 深度内容提取 ──
    if use_content_extraction:
        report(6, "深度内容提取", "图片内容已在前序步骤完成提取", 1.0)

    # ── 组装结果 ──
    diagnostics = analyze_report_quality(parsed, image_bytes_list=None)

    # 将融合后的图片结论注入 diagnostics
    diagnostics["image_findings"] = _build_image_findings_from_contexts(img_results, contexts)
    diagnostics["extracted_image_text"] = merged.image_text_to_merge

    # 统计
    stats = _count_image_types(img_results)

    return PipelineResult(
        parsed=parsed,
        condensation=condensation,
        key_parameters=key_params,
        image_contexts=contexts,
        image_results=img_results,
        diagnostics=diagnostics,
        merged_findings=merged.findings,
        merged_report=merged.summary,
        total_images=len(img_results),
        waveform_images=stats.get("波形图", 0),
        table_images=stats.get("表格", 0),
        code_screenshot_images=stats.get("代码截图", 0),
        blurry_images=stats.get("模糊", 0),
        empty_waveform_images=stats.get("空波形", 0),
    )


def _enrich_image_findings_with_context(
    img_results: list[ImageAnalysisResult],
    contexts: list[ImageContext],
) -> None:
    """将图片的上下文位置信息写入分析结果的 description 字段。"""
    for i, result in enumerate(img_results):
        if i < len(contexts):
            ctx = contexts[i]
            location = f"[第{ctx.page_number}页, {ctx.nearest_section}]" if ctx.page_number > 0 else f"[{ctx.nearest_section}]"
            result.content_type.description = f"{result.content_type.description} — 位于 {location}"


def _count_image_types(img_results: list[ImageAnalysisResult]) -> dict[str, int]:
    """统计图片类型和问题数量。"""
    stats: dict[str, int] = {}
    for r in img_results:
        label = r.content_type.label
        name_map = {
            ImageLabel.WAVEFORM: "波形图",
            ImageLabel.TABLE: "表格",
            ImageLabel.CODE_SCREENSHOT: "代码截图",
            ImageLabel.CIRCUIT_DIAGRAM: "电路图",
            ImageLabel.TEXT_SCAN: "文本扫描",
            ImageLabel.PHOTO: "照片",
            ImageLabel.UNKNOWN: "未知类型",
        }
        name = name_map.get(label, label.value)
        stats[name] = stats.get(name, 0) + 1

        if r.quality.is_blurry:
            stats["模糊"] = stats.get("模糊", 0) + 1
        if r.waveform_content and not r.waveform_content.has_signal:
            stats["空波形"] = stats.get("空波形", 0) + 1
    return stats


def _build_image_findings_from_contexts(
    img_results: list[ImageAnalysisResult],
    contexts: list[ImageContext],
) -> list[str]:
    """构建带位置信息的图片分析 findings。"""
    findings = [f"检测到图片对象：{len(img_results)} 个。"]
    for i, (result, ctx) in enumerate(zip(img_results, contexts), start=1):
        location = f"第{ctx.page_number}页" if ctx.page_number > 0 else f"位置{i}"
        findings.append(result.content_type.to_message(i))
        findings.append(f"  📍 位于 {location}，{ctx.nearest_section}")

        if result.quality.warnings:
            for w in result.quality.warnings:
                findings.append(f"  ⚠ {w}")

        if result.waveform_content:
            findings.append(f"  📊 {result.waveform_content.description}")
        if result.table_content and result.table_content.rows > 0:
            findings.append(f"  📋 {result.table_content.rows}×{result.table_content.cols} 表格")
    return findings
