"""文本+图片综合分析融合模块。

将文本凝练结果和图片分析结果融合，生成：
1. 每张图片的文本上下文验证
2. 图片类型与所在章节的交叉检查
3. 统一的分析报告
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.parser.document_parser import ImageContext
from src.vision.image_processor import ImageAnalysisResult, ImageLabel


@dataclass
class MergedAnalysis:
    """文本+图片融合分析结果。"""
    findings: list[str]           # 融合后的逐条发现
    summary: str                  # 综合分析摘要
    image_text_to_merge: str      # 应从图片提取的文本（用于汇入报告正文）
    cross_validations: list[str]  # 交叉验证结果


def merge_text_image_analysis(
    condensed_text: str,
    key_parameters: dict[str, list[str]],
    image_results: list[ImageAnalysisResult],
    image_contexts: list[ImageContext],
) -> MergedAnalysis:
    """融合文本和图片分析，生成综合报告。

    Args:
        condensed_text: 凝练后的报告文本。
        key_parameters: 从原文提取的关键技术参数。
        image_results: 图片分析结果列表。
        image_contexts: 图片上下文位置列表。

    Returns:
        MergedAnalysis 融合结果。
    """
    findings: list[str] = []
    cross_validations: list[str] = []
    image_text_parts: list[str] = []

    # ── 文本概况 ──
    param_count = sum(len(v) for v in key_parameters.values())
    if param_count > 0:
        param_summary = []
        for cat, vals in key_parameters.items():
            if vals:
                param_summary.append(f"{cat}({len(vals)}个: {', '.join(vals[:5])})")
        findings.append(f"文本提取关键技术参数 {param_count} 个：{'；'.join(param_summary)}")
    else:
        findings.append("未从文本中提取到明显技术参数，建议补充定量描述。")

    # ── 图片概况 ──
    findings.append(f"共检测图片 {len(image_results)} 张。")

    # ── 逐图交叉验证 ──
    for i, (result, ctx) in enumerate(zip(image_results, image_contexts), start=1):
        label = result.content_type.label
        section = ctx.nearest_section

        # 交叉验证：图片类型 vs 所在章节
        cv = _cross_validate(label, section, i)
        if cv:
            cross_validations.append(cv)

        # 图片提取文本
        if result.extracted_text:
            image_text_parts.append(f"[图{i} OCR文本]\n{result.extracted_text}")
        if result.table_content and result.table_content.raw_text:
            image_text_parts.append(f"[图{i} 表格内容]\n{result.table_content.raw_text}")

        # 波形空信号警告
        if result.waveform_content and not result.waveform_content.has_signal:
            cross_validations.append(
                f"图{i}（{section}）：疑似空白坐标系/无信号数据 — 请确认该截图是否为有效测量结果。"
            )

    # ── 生成摘要 ──
    summary_parts = [
        f"## 综合分析摘要",
        f"",
        f"**文本概况**：原文经智能凝练后保留了关键技术参数和代码块。",
    ]
    if param_count > 0:
        summary_parts.append(f"提取到 {param_count} 个技术参数，涵盖 {len(key_parameters)} 个类别。")
    summary_parts.append(f"")
    summary_parts.append(f"**图片概况**：共 {len(image_results)} 张图片，已完成分类和内容分析。")

    if cross_validations:
        summary_parts.append(f"")
        summary_parts.append(f"**交叉验证发现**：")
        for cv in cross_validations:
            summary_parts.append(f"- {cv}")

    summary = "\n".join(summary_parts)

    return MergedAnalysis(
        findings=findings + cross_validations,
        summary=summary,
        image_text_to_merge="\n\n".join(image_text_parts),
        cross_validations=cross_validations,
    )


def _cross_validate(label: ImageLabel, section: str, index: int) -> str | None:
    """交叉验证图片类型与所在章节是否匹配。

    返回警告字符串，若匹配正常则返回 None。
    """
    # 合理的搭配
    valid_pairs = {
        ImageLabel.WAVEFORM: {"运行结果", "结果分析", "实验步骤", "实验过程"},
        ImageLabel.TABLE: {"实验环境", "实验步骤", "实验过程", "运行结果", "结果分析"},
        ImageLabel.CODE_SCREENSHOT: {"核心代码", "实验步骤", "实验过程"},
        ImageLabel.CIRCUIT_DIAGRAM: {"实验原理", "实验环境", "实验步骤"},
        ImageLabel.TEXT_SCAN: {"实验原理", "实验步骤", "参考资料"},
    }

    # 不合理的搭配
    suspicious_pairs = {
        ImageLabel.CODE_SCREENSHOT: {"实验总结", "实验结果", "参考资料"},
        ImageLabel.WAVEFORM: {"实验目的", "参考资料"},
        ImageLabel.TABLE: {"实验总结", "实验目的"},
    }

    expected = valid_pairs.get(label, set())
    suspicious = suspicious_pairs.get(label, set())

    if section in suspicious:
        return f"⚠ 图{index}：{label.value} 出现在「{section}」章节，位置可能不当。"

    if expected and section not in expected and section != "未知章节":
        return f"💡 图{index}：{label.value} 出现在「{section}」章节（通常在 {', '.join(expected)} 中出现）。"

    return None
