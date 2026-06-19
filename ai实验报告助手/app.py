from pathlib import Path

import pandas as pd
import streamlit as st

from src.analyzer.pipeline import PipelineProgress, run_analysis_pipeline
from src.classifier.course_classifier import classify_course_by_rules
from src.evaluator.llm_evaluator import LLMEvaluationError, evaluate_with_openai_compatible_api
from src.evaluator.rubric_loader import list_rubrics, load_rubric
from src.exporter.report_exporter import export_markdown_review
from src.parser.document_parser import render_pdf_page_previews
from src.parser.ocr_parser import extract_visual_text
from src.utils.settings import load_settings


st.set_page_config(
    page_title="实验报告智能检测与反馈系统",
    page_icon="",
    layout="wide",
)


def main() -> None:
    st.title("面向计算机类课程的实验报告智能检测与反馈系统")
    st.caption("上传实验报告，系统将并行解析文本与图片，智能凝练后生成检测反馈。")

    rubrics = list_rubrics()
    course_options = {"auto": "自动识别"}
    course_options.update({item["course_type"]: item["course_name"] for item in rubrics})
    settings = load_settings()
    llm_ready = _is_llm_configured(settings)

    with st.sidebar:
        st.header("检测设置")
        st.caption("1. 上传报告")
        uploaded_file = st.file_uploader(
            "上传实验报告",
            type=["docx", "pdf", "txt", "md"],
        )
        if uploaded_file:
            st.success(f"已上传：{uploaded_file.name}")
        selected_course = st.selectbox(
            "课程类型",
            options=list(course_options.keys()),
            format_func=lambda key: course_options[key],
        )
        st.caption("2. 选择评阅方式")
        use_llm = st.checkbox("启用大模型评阅", value=False)
        use_ocr = st.checkbox("读取图片/扫描页文字 OCR", value=False)
        use_deep_image = st.checkbox("深度分析图片内容（表格OCR/波形检测，较慢）", value=False)
        if llm_ready:
            st.success(f"模型配置：{settings['llm']['model']}")
        else:
            st.warning("尚未填写 DeepSeek API Key，可先使用规则检测。")
        st.caption("3. 开始检测")
        start = st.button("开始检测", type="primary", use_container_width=True)

    if not uploaded_file:
        _render_empty_state(course_options)
        return

    uploaded_bytes = uploaded_file.getvalue()

    # ── 流水线分析 ──
    pipeline_result = _run_pipeline_with_progress(
        uploaded_file, use_content_extraction=use_deep_image,
    )
    parsed = pipeline_result.parsed
    diagnostics = pipeline_result.diagnostics

    # ── OCR 补充 ──
    ocr_result = None
    if use_ocr and parsed.file_type in {"pdf", "docx"}:
        max_pages = settings.get("app", {}).get("ocr_max_pages", 5)
        with st.spinner("正在进行图片/扫描页 OCR 识别..."):
            ocr_result = extract_visual_text(parsed.file_type, uploaded_bytes, max_pages=max_pages)
        if ocr_result and ocr_result.text.strip():
            parsed.full_text = _merge_ocr_text(parsed.full_text, ocr_result.text)

    # ── 展示解析预览 ──
    _render_parsed_summary(pipeline_result, parsed, diagnostics, uploaded_bytes, ocr_result)

    if not start:
        st.info("确认解析内容无误后，点击左侧「开始检测」。")
        return

    # ── 课程分类 → 评阅 ──
    if selected_course == "auto":
        course_result = classify_course_by_rules(pipeline_result.condensation.condensed_text)
        course_type = course_result["course_type"]
    else:
        course_type = selected_course
        course_result = {
            "course_type": selected_course,
            "course_name": course_options[selected_course],
            "confidence": 1.0,
            "reason": "用户手动选择课程类型。",
        }

    if course_type == "unknown":
        st.warning("未能可靠识别课程类型，请在左侧手动选择后重新检测。")
        return

    rubric = load_rubric(course_type)

    # 使用凝练后的文本 + 图片融合报告发送给 LLM
    review_text = pipeline_result.condensation.condensed_text
    if pipeline_result.merged_report:
        review_text += "\n\n--- 图片分析融合报告 ---\n" + pipeline_result.merged_report

    if use_llm:
        try:
            prompt_template = Path("prompts/report_review_prompt.txt").read_text(encoding="utf-8")
            with st.spinner("正在调用大模型评阅（DeepSeek API，约需 1-3 分钟，请耐心等待）..."):
                review = evaluate_with_openai_compatible_api(
                    review_text,
                    rubric,
                    settings,
                    prompt_template,
                    diagnostics,
                )
        except (FileNotFoundError, KeyError, ValueError, LLMEvaluationError) as exc:
            st.error(f"大模型评阅失败：{exc}")
            st.info("请检查 config/settings.json 中的 base_url、api_key 和 model 配置。")
            return
    else:
        review = build_placeholder_review(review_text, rubric, course_result, use_llm, diagnostics)

    _render_review(course_result, review, use_llm, diagnostics)

    markdown = export_markdown_review(parsed.file_name, course_result, review)
    with st.container(border=True):
        st.subheader("导出结果")
        st.download_button(
            "下载 Markdown 检测报告",
            data=markdown,
            file_name=f"{Path(parsed.file_name).stem}_检测报告.md",
            mime="text/markdown",
            use_container_width=True,
        )


# ── 流水线进度面板 ──────────────────────────────────────


def _run_pipeline_with_progress(uploaded_file, use_content_extraction: bool = False):
    """运行分析流水线并通过 st.status 展示实时进度。"""
    progress_container = st.empty()

    progress_steps: list[PipelineProgress] = []

    def on_progress(p: PipelineProgress):
        progress_steps.append(p)

    with st.status("正在分析实验报告...", expanded=True) as status:
        placeholder = st.empty()

        # 启动流水线（在后台线程中运行，但由于 st.status 是阻塞上下文，我们逐步骤展示）
        # 使用 Pipeline 直接在主线程运行，每步手动更新
        from src.analyzer.pipeline import (
            CondensationResult,
            PipelineResult,
            condense_report_text,
            extract_key_parameters,
        )
        from src.parser.document_parser import (
            extract_document_images_with_context,
            parse_uploaded_file,
        )
        from src.vision.image_processor import analyze_images_from_bytes
        from src.evaluator.report_analyzer import analyze_report_quality
        from src.analyzer.result_merger import merge_text_image_analysis
        import concurrent.futures

        # Step 1
        st.write("🔍 解析文档结构...")
        parsed = parse_uploaded_file(uploaded_file)
        st.write(f"✓ 文档解析完成 — {parsed.page_count} 页, {parsed.image_count} 张图片, {len(parsed.full_text)} 字符")

        # Step 2: 并行文本凝练 + 图片提取分析
        st.write("📝 文本智能凝练 & 🖼️ 图片分类分析（并行执行）...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            text_future = executor.submit(condense_report_text, parsed.full_text, 6000)

            def _img_task():
                contexts = extract_document_images_with_context(uploaded_file)
                if contexts:
                    results, extracted = analyze_images_from_bytes(
                        [c.image_bytes for c in contexts],
                        extract_content=use_content_extraction,
                    )
                else:
                    results, extracted = [], 0
                return contexts, results, extracted

            img_future = executor.submit(_img_task)

            condensation: CondensationResult = text_future.result()
            contexts, img_results, extracted_count = img_future.result()

        reduction = (1 - condensation.condensed_length / max(1, condensation.original_length)) * 100
        st.write(f"✓ 文本: {condensation.original_length} → {condensation.condensed_length} 字符 (精简 {reduction:.0f}%)")
        st.write(f"✓ 图片: {len(img_results)} 张已分类（深度提取 {extracted_count} 张）")

        # Step 3
        st.write("🔑 提取关键技术参数...")
        key_params = extract_key_parameters(parsed.full_text)
        param_count = sum(len(v) for v in key_params.values())
        if param_count > 0:
            cat_list = "、".join(f"{k}({len(v)}项)" for k, v in key_params.items() if v)
            st.write(f"✓ 提取 {param_count} 个参数：{cat_list}")
        else:
            st.write("✓ 未提取到明显技术参数")

        # Step 4
        st.write("🔗 图片-文本位置关联...")
        if contexts and img_results:
            from src.analyzer.pipeline import _enrich_image_findings_with_context, _count_image_types
            _enrich_image_findings_with_context(img_results, contexts)
            stats = _count_image_types(img_results)
            detail = "、".join(f"{k}: {v}张" for k, v in stats.items() if v > 0)
            st.write(f"✓ 关联完成 — {detail}")
        else:
            st.write("✓ 无图片可关联")

        # Step 5
        st.write("🔬 综合分析融合...")
        merged = merge_text_image_analysis(
            condensation.condensed_text,
            key_params,
            img_results,
            contexts,
        )
        st.write(f"✓ 融合分析完成 — {len(merged.findings)} 项发现, {len(merged.cross_validations)} 项交叉验证")

        # 组装 diagnostics
        diagnostics = analyze_report_quality(parsed, image_bytes_list=None)

        from src.analyzer.pipeline import _build_image_findings_from_contexts
        diagnostics["image_findings"] = _build_image_findings_from_contexts(img_results, contexts)
        diagnostics["extracted_image_text"] = merged.image_text_to_merge

        status.update(label="分析完成 ✓", state="complete", expanded=False)

    # 组装结果
    stats = {}
    for r in img_results:
        from src.vision.image_processor import ImageLabel
        name_map = {
            ImageLabel.WAVEFORM: "波形图", ImageLabel.TABLE: "表格",
            ImageLabel.CODE_SCREENSHOT: "代码截图", ImageLabel.CIRCUIT_DIAGRAM: "电路图",
        }
        name = name_map.get(r.content_type.label, r.content_type.label.value)
        stats[name] = stats.get(name, 0) + 1
        if r.quality.is_blurry:
            stats["模糊"] = stats.get("模糊", 0) + 1

    from src.analyzer.pipeline import PipelineResult
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
    )


# ── 解析预览 ────────────────────────────────────────────


def _render_parsed_summary(pipeline_result, parsed, diagnostics: dict, uploaded_bytes: bytes, ocr_result) -> None:
    st.subheader("解析预览")
    cond = pipeline_result.condensation

    cols = st.columns(7)
    cols[0].metric("文件名", parsed.file_name)
    cols[1].metric("文件类型", parsed.file_type)
    cols[2].metric("原始文本", f"{cond.original_length} 字符")
    cols[3].metric("凝练后", f"{cond.condensed_length} 字符", f"-{(1 - cond.condensed_length / max(1, cond.original_length)) * 100:.0f}%")
    cols[4].metric("页数", parsed.page_count or "-")
    cols[5].metric("图片", parsed.image_count)
    cols[6].metric("代码块", f"{len(parsed.code_blocks)} 个")

    # 关键参数摘要
    if pipeline_result.key_parameters:
        with st.expander("提取的关键技术参数"):
            for cat, vals in pipeline_result.key_parameters.items():
                if vals:
                    st.caption(f"**{cat}**：{', '.join(vals[:10])}")

    tabs = st.tabs(["凝练预览", "原文对比", "格式与图片", "OCR 文本", "预检诊断", "代码块", "表格"])
    with tabs[0]:
        st.caption(f"智能凝练：{cond.original_length} → {cond.condensed_length} 字符（保留章节/代码/参数/结论）")
        st.text_area("凝练后文本", cond.condensed_text[:6000], height=320)

    with tabs[1]:
        st.text_area("原文（前 5000 字符）", parsed.full_text[:5000], height=320)

    with tabs[2]:
        st.markdown("**图片检测**")
        for finding in diagnostics["image_findings"]:
            if "代码截图" in finding or "代码应以文字" in finding:
                st.warning(finding)
            elif "质量警告" in finding or "模糊" in finding or "对比度偏低" in finding:
                st.warning(finding)
            elif finding.startswith("[图") and "置信度" in finding:
                st.info(finding)
            elif finding.startswith("  📍") or finding.startswith("  📊") or finding.startswith("  📋"):
                st.caption(finding)
            elif finding.startswith("  ⚠"):
                st.warning(finding)
            else:
                st.write("- " + finding)

        if pipeline_result.merged_report:
            with st.expander("查看综合分析摘要"):
                st.markdown(pipeline_result.merged_report)

        if parsed.file_type == "pdf" and parsed.page_count:
            with st.expander("查看 PDF 前 3 页页面预览"):
                try:
                    previews = render_pdf_page_previews(uploaded_bytes, max_pages=3)
                    for index, image_bytes in enumerate(previews, start=1):
                        st.image(image_bytes, caption=f"第 {index} 页预览", use_container_width=True)
                except Exception as exc:
                    st.warning(f"页面预览生成失败：{exc}")
        elif parsed.file_type == "docx" and parsed.image_count:
            st.info("DOCX 已检测到图片对象。当前界面暂不展开 DOCX 内嵌图片预览。")

    with tabs[3]:
        if not ocr_result:
            st.info("未启用 OCR。若报告包含扫描页、截图文字、波形标注或图片代码，可在左侧勾选「读取图片/扫描页文字 OCR」。")
        else:
            cols = st.columns(3)
            cols[0].metric("OCR 页数", ocr_result.page_count or "-")
            cols[1].metric("OCR 图片", ocr_result.image_count)
            cols[2].metric("OCR 文本长度", len(ocr_result.text))
            for warning in ocr_result.warnings:
                st.warning(warning)
            if ocr_result.text.strip():
                st.text_area("图片/扫描页 OCR 识别文本", ocr_result.text[:8000], height=320)
            else:
                st.info("OCR 未识别到有效文字。图片可能主要是波形、照片或图像质量较低。")

    with tabs[4]:
        st.metric("预检分", f"{diagnostics['precheck_score']} / 100")
        st.write("已识别章节：", "、".join(diagnostics["detected_sections"]) or "无")
        st.write("可能缺失章节：", "、".join(diagnostics["missing_sections"]) or "无")
        marker_df = pd.DataFrame(
            [{"类别": key, "命中次数": value} for key, value in diagnostics["technical_markers"].items()]
        )
        st.dataframe(marker_df, use_container_width=True, hide_index=True)
        for note in diagnostics["precheck_notes"]:
            st.warning(note)

    with tabs[5]:
        if parsed.code_blocks:
            for index, code in enumerate(parsed.code_blocks, start=1):
                st.code(code, language="python")
                st.caption(f"代码块 {index}")
        else:
            st.info("未识别到 Markdown 代码块。")

    with tabs[6]:
        if parsed.tables:
            for index, table in enumerate(parsed.tables, start=1):
                st.text_area(f"表格 {index}", table, height=160)
        else:
            st.info("未识别到表格。")


# ── 评阅展示 ────────────────────────────────────────────


def _render_review(course_result: dict, review: dict, use_llm: bool, diagnostics: dict) -> None:
    st.subheader("检测结果")
    score = int(review["total_score"])
    score_level = _score_level(score)

    cols = st.columns(4)
    cols[0].metric("总分", f"{score} / 100", score_level)
    cols[1].metric("课程类型", course_result["course_name"])
    cols[2].metric("问题数量", len(review["problems"]))
    cols[3].metric("评阅方式", "DeepSeek 大模型" if use_llm else "规则占位")
    st.caption(f"识别理由：{course_result['reason']}")
    st.caption(f"系统预检分：{diagnostics['precheck_score']} / 100；该分数作为辅助诊断，不直接替代模型总分。")

    tabs = st.tabs(["分项评分", "问题建议", "教师评语", "风险提示", "原始 JSON"])
    with tabs[0]:
        df = pd.DataFrame(review["dimension_scores"])
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tabs[1]:
        if not review["problems"]:
            st.success("未发现明显问题。")
        for index, problem in enumerate(review["problems"], start=1):
            with st.container(border=True):
                st.markdown(f"**{index}. {problem['type']}**")
                st.caption(f"位置：{problem['location']}")
                st.write(problem["description"])
                st.info(problem["suggestion"])

    with tabs[2]:
        st.success(review["teacher_comment"])

    with tabs[3]:
        if review["risk_warnings"]:
            for warning in review["risk_warnings"]:
                st.warning(warning)
        else:
            st.success("未发现明显风险提示。")

    with tabs[4]:
        st.json(review)


# ── 辅助函数 ────────────────────────────────────────────


def build_placeholder_review(report_text: str, rubric: dict, course_result: dict, use_llm: bool, diagnostics: dict | None = None) -> dict:
    """Temporary review output before the LLM evaluator is implemented."""
    missing_sections = []
    if diagnostics:
        missing_sections = diagnostics.get("missing_sections", [])
    else:
        for section in ["实验目的", "实验环境", "实验原理", "实验步骤", "运行结果", "结果分析", "实验总结"]:
            if section not in report_text:
                missing_sections.append(section)

    dimension_scores = []
    total = 0
    for item in rubric["dimensions"]:
        max_score = item["max_score"]
        score = max_score
        if item["name"] == "结构完整性":
            score = max(0, max_score - len(missing_sections) * 2)
        elif item["name"] == "风险提示" and len(report_text) < 1200:
            score = max_score - 2
        else:
            score = int(max_score * 0.8)
        total += score
        dimension_scores.append(
            {
                "dimension": item["name"],
                "score": score,
                "max_score": max_score,
                "comment": item["criteria"],
            }
        )

    problems = []
    if missing_sections:
        problems.append(
            {
                "type": "结构缺失",
                "location": "报告整体结构",
                "description": "报告可能缺少以下常见章节：" + "、".join(missing_sections),
                "suggestion": "建议补充缺失章节，并结合具体实验过程填写内容。",
            }
        )
    if len(report_text) < 1200:
        problems.append(
            {
                "type": "内容偏少",
                "location": "报告正文",
                "description": "当前报告文本较短，可能不足以支撑完整的实验分析。",
                "suggestion": "建议补充实验步骤、关键代码说明、测试样例和结果分析。",
            }
        )
    if diagnostics:
        for note in diagnostics.get("precheck_notes", []):
            problems.append(
                {
                    "type": "系统预检",
                    "location": "报告整体",
                    "description": note,
                    "suggestion": "建议结合课程要求补充对应内容，并在报告中提供可核验的过程或结果证据。",
                }
            )
    if use_llm:
        problems.append(
            {
                "type": "功能待实现",
                "location": "LLM 评阅模块",
                "description": "当前项目骨架尚未接入真实大模型。",
                "suggestion": "请在 src/evaluator/llm_evaluator.py 中实现模型调用。",
            }
        )

    return {
        "summary": "当前结果由规则骨架生成，后续可替换为大模型评阅结果。",
        "total_score": min(total, 100),
        "dimension_scores": dimension_scores,
        "problems": problems,
        "teacher_comment": f"该报告已识别为{course_result['course_name']}方向，建议继续完善实验过程、结果分析和技术细节。",
        "risk_warnings": ["当前为规则骨架结果，不能替代教师最终评阅。"] if use_llm else [],
    }


def _merge_ocr_text(original_text: str, ocr_text: str) -> str:
    return f"{original_text.strip()}\n\n--- 图片/扫描页 OCR 识别文本 ---\n\n{ocr_text.strip()}"


def _is_llm_configured(settings: dict) -> bool:
    llm = settings.get("llm", {})
    api_key = llm.get("api_key", "")
    return bool(llm.get("base_url") and llm.get("model") and api_key and "API Key" not in api_key and api_key != "YOUR_API_KEY_HERE")


def _render_empty_state(course_options: dict) -> None:
    st.info("请先上传一份 DOCX、PDF、TXT 或 Markdown 格式的实验报告。")
    cols = st.columns(3)
    cards = [
        ("支持格式", "DOCX / PDF / TXT / Markdown"),
        ("支持课程", "程序设计、数据结构、数据库、操作系统、计网、AI/ML"),
        ("输出内容", "总分、分项评分、问题定位、修改建议、教师评语"),
    ]
    for col, (title, body) in zip(cols, cards):
        with col:
            st.container(border=True).markdown(f"**{title}**\n\n{body}")

    with st.expander("当前可选课程类型"):
        st.write("、".join(name for key, name in course_options.items() if key != "auto"))


def _score_level(score: int) -> str:
    if score >= 90:
        return "优秀"
    if score >= 80:
        return "良好"
    if score >= 70:
        return "中等"
    if score >= 60:
        return "及格"
    return "需修改"


if __name__ == "__main__":
    main()
