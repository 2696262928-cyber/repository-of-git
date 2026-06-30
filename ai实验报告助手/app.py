import html
from pathlib import Path

import pandas as pd
import streamlit as st

from src.analyzer.pipeline import PipelineProgress, run_analysis_pipeline
from src.classifier.course_classifier import classify_course_by_rules
from src.evaluator.llm_evaluator import (
    LLMEvaluationError,
    TASK_DEFINITIONS,
    build_task_rag_query,
    evaluate_task_with_openai_compatible_api,
    load_prompt_template,
)
from src.evaluator.rubric_loader import list_rubrics, load_rubric
from src.exporter.report_exporter import export_docx_review, export_markdown_review
from src.parser.document_parser import render_pdf_page_previews
from src.parser.ocr_parser import extract_visual_text
from src.retriever.simple_retriever import format_knowledge_for_prompt, retrieve_knowledge
from src.utils.feedback import append_feedback_record, load_feedback
from src.utils.history import append_history_record, load_history
from src.utils.settings import load_settings


st.set_page_config(
    page_title="实验报告智能检测与反馈系统",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _inject_global_styles() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {
            display: none !important;
            visibility: hidden !important;
        }
        header {visibility: hidden;}
        .block-container {
            max-width: 1380px;
            padding-top: 1.6rem;
            padding-bottom: 3rem;
        }
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stMarkdownContainer"] li,
        .stAlert,
        .stText {
            word-break: break-word;
            overflow-wrap: anywhere;
            line-height: 1.65;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .35rem;
            flex-wrap: wrap;
        }
        .stTabs [data-baseweb="tab"] {
            height: 2.55rem;
            border-radius: 999px;
            padding: 0 .9rem;
            background: #f7f8fb;
        }
        .hero-card {
            padding: 1.35rem 1.5rem;
            border: 1px solid #e8edf5;
            border-radius: 18px;
            background: linear-gradient(135deg, #f6f9ff 0%, #ffffff 58%, #f7fbff 100%);
            box-shadow: 0 10px 28px rgba(31, 78, 121, .06);
            margin-bottom: 1rem;
        }
        .hero-card h1 {
            margin: 0 0 .35rem 0;
            font-size: 2rem;
            letter-spacing: -.02em;
        }
        .hero-card p {
            margin: 0;
            color: #4b5563;
            font-size: 1rem;
        }
        .soft-card {
            border: 1px solid #e7edf6;
            border-radius: 16px;
            background: #ffffff;
            padding: 1rem 1.1rem;
            margin: .7rem 0;
            box-shadow: 0 6px 20px rgba(17, 24, 39, .045);
        }
        .score-card-header, .problem-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .8rem;
            margin-bottom: .55rem;
        }
        .score-title, .problem-title {
            font-weight: 700;
            font-size: 1.02rem;
            color: #111827;
        }
        .score-pill, .tag-pill {
            flex: 0 0 auto;
            border-radius: 999px;
            padding: .22rem .62rem;
            background: #eff6ff;
            color: #1d4ed8;
            font-weight: 700;
            font-size: .86rem;
        }
        .bar-track {
            width: 100%;
            height: .62rem;
            border-radius: 999px;
            background: #edf2f7;
            overflow: hidden;
            margin: .45rem 0 .65rem 0;
        }
        .bar-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #2563eb, #22c55e);
        }
        .card-muted {
            color: #4b5563;
            margin: .25rem 0 0 0;
            line-height: 1.65;
        }
        .problem-location {
            color: #64748b;
            font-size: .9rem;
            margin: -.15rem 0 .55rem 0;
        }
        .suggestion-box {
            border-left: 4px solid #2563eb;
            border-radius: 10px;
            background: #f8fbff;
            padding: .7rem .85rem;
            margin-top: .65rem;
            color: #1f2937;
        }
        .summary-card {
            border: 1px solid #dbeafe;
            border-radius: 16px;
            background: #f8fbff;
            padding: .9rem 1rem;
            margin: .8rem 0 1rem 0;
            color: #1e3a8a;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
            gap: .75rem;
            margin: .8rem 0 1.1rem 0;
        }
        .metric-card {
            min-width: 0;
            border: 1px solid #e7edf6;
            border-radius: 15px;
            background: #ffffff;
            padding: .78rem .9rem;
            box-shadow: 0 5px 16px rgba(17, 24, 39, .04);
        }
        .metric-label {
            color: #64748b;
            font-size: .82rem;
            margin-bottom: .28rem;
            white-space: normal;
        }
        .metric-value {
            color: #111827;
            font-size: 1.03rem;
            font-weight: 750;
            line-height: 1.35;
            white-space: normal;
            word-break: break-word;
            overflow-wrap: anywhere;
        }
        .metric-delta {
            color: #2563eb;
            font-size: .82rem;
            margin-top: .18rem;
            white-space: normal;
            word-break: break-word;
        }
        .json-wrap pre {
            white-space: pre-wrap !important;
            word-break: break-word !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_hero() -> None:
    st.markdown(
        """
        <div class="hero-card">
          <h1>面向计算机类课程的实验报告智能检测与反馈系统</h1>
          <p>上传实验报告后，系统会并行解析文本与图片、召回本地课程知识库，并生成评分、问题定位和修改建议。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    _inject_global_styles()
    _render_hero()

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
        st.caption("3. 知识库增强")
        use_rag = st.checkbox("启用本地知识库 RAG", value=True)
        rag_top_k = st.slider("RAG 召回片段数", min_value=1, max_value=5, value=3, disabled=not use_rag)
        rag_max_chars = st.slider("RAG 上下文长度", min_value=600, max_value=2400, value=1200, step=300, disabled=not use_rag)
        show_rag_refs = st.checkbox("显示 RAG 引用片段", value=True, disabled=not use_rag)
        if llm_ready:
            st.success(f"模型配置：{settings['llm']['model']}")
        else:
            st.warning("尚未填写 DeepSeek API Key，可先使用规则检测。")
        st.caption("4. 开始检测")
        if uploaded_file:
            st.info("提示：请先在主页面顶部选择任务模式，并填写自己的需求或问题。")
        start = st.button("开始检测", type="primary", use_container_width=True)
        _render_history_sidebar()

    if not uploaded_file:
        _render_empty_state(course_options)
        return

    uploaded_bytes = uploaded_file.getvalue()
    task_type, user_instruction = _render_task_config(use_llm)

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
    detection_signature = _build_detection_signature(
        parsed.file_name,
        selected_course,
        task_type,
        user_instruction,
        use_llm,
        use_rag,
        use_ocr,
        use_deep_image,
    )

    if not start:
        cached = _get_cached_detection_result(detection_signature)
        if cached:
            if cached["use_rag"] and show_rag_refs:
                _render_knowledge_context(cached["knowledge_snippets"])
            st.info("已保留上一次检测结果。修改任务、需求或设置后，请重新点击左侧「开始检测」。")
            _render_detection_output(
                cached["file_name"],
                cached["course_result"],
                cached["review"],
                cached["diagnostics"],
                cached["task_type"],
                cached["user_instruction"],
                cached["use_llm"],
                cached["use_rag"],
                cached["knowledge_snippets"],
            )
            return
        st.info("确认任务模式、用户需求和解析内容无误后，点击左侧「开始检测」。")
        return
    if TASK_DEFINITIONS[task_type]["requires_instruction"] and not user_instruction.strip():
        st.error(f"当前任务「{TASK_DEFINITIONS[task_type]['label']}」需要填写「我的需求 / 问题 / 关注点」。")
        return
    if not use_llm and task_type != "report_review":
        st.warning("当前未启用大模型，非全面评阅任务会回退为规则基础评阅结果。")

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

    rag_query = build_task_rag_query(review_text, task_type, user_instruction)
    knowledge_snippets = retrieve_knowledge(rag_query, course_type, top_k=rag_top_k, max_chars=rag_max_chars) if use_rag else []
    knowledge_context = format_knowledge_for_prompt(knowledge_snippets) if use_rag else "未启用本地课程知识库 RAG。"
    if use_rag and show_rag_refs:
        _render_knowledge_context(knowledge_snippets)

    if use_llm:
        try:
            prompt_template = load_prompt_template(task_type)
            with st.spinner(f"正在调用大模型执行「{TASK_DEFINITIONS[task_type]['label']}」（约需 1-3 分钟）..."):
                review = evaluate_task_with_openai_compatible_api(
                    review_text,
                    rubric,
                    settings,
                    prompt_template,
                    diagnostics,
                    knowledge_context=knowledge_context,
                    task_type=task_type,
                    user_instruction=user_instruction,
                )
        except (FileNotFoundError, KeyError, ValueError, LLMEvaluationError) as exc:
            st.error(f"大模型评阅失败：{exc}")
            st.info("请检查 config/settings.json 中的 base_url、api_key 和 model 配置。")
            return
    else:
        review = build_placeholder_review(review_text, rubric, course_result, use_llm, diagnostics)

    _cache_detection_result(
        detection_signature,
        parsed.file_name,
        course_result,
        review,
        diagnostics,
        task_type,
        user_instruction,
        use_llm,
        use_rag,
        knowledge_snippets,
    )
    _render_detection_output(
        parsed.file_name,
        course_result,
        review,
        diagnostics,
        task_type,
        user_instruction,
        use_llm,
        use_rag,
        knowledge_snippets,
            )


def _render_detection_output(
    file_name: str,
    course_result: dict,
    review: dict,
    diagnostics: dict,
    task_type: str,
    user_instruction: str,
    use_llm: bool,
    use_rag: bool,
    knowledge_snippets: list[dict],
) -> None:
    _save_detection_history(file_name, course_result, review, use_llm, use_rag, knowledge_snippets, task_type, user_instruction)
    _render_task_result(course_result, review, use_llm, diagnostics, task_type, user_instruction)

    markdown = export_markdown_review(file_name, course_result, review, knowledge_snippets, task_type, user_instruction)
    docx = export_docx_review(file_name, course_result, review, knowledge_snippets, task_type, user_instruction)
    with st.container(border=True):
        st.subheader("导出结果")
        col_md, col_docx = st.columns(2)
        with col_md:
            st.download_button(
                "下载 Markdown 检测报告",
                data=markdown,
                file_name=f"{Path(file_name).stem}_检测报告.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_docx:
            st.download_button(
                "下载 Word 检测报告",
                data=docx,
                file_name=f"{Path(file_name).stem}_检测报告.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
    _render_feedback_section(file_name, course_result, review, task_type, user_instruction, use_llm, use_rag, knowledge_snippets)


def _build_detection_signature(
    file_name: str,
    selected_course: str,
    task_type: str,
    user_instruction: str,
    use_llm: bool,
    use_rag: bool,
    use_ocr: bool,
    use_deep_image: bool,
) -> str:
    return "|".join(
        [
            file_name,
            selected_course,
            task_type,
            user_instruction,
            str(use_llm),
            str(use_rag),
            str(use_ocr),
            str(use_deep_image),
        ]
    )


def _cache_detection_result(
    signature: str,
    file_name: str,
    course_result: dict,
    review: dict,
    diagnostics: dict,
    task_type: str,
    user_instruction: str,
    use_llm: bool,
    use_rag: bool,
    knowledge_snippets: list[dict],
) -> None:
    st.session_state["last_detection_result"] = {
        "signature": signature,
        "file_name": file_name,
        "course_result": course_result,
        "review": review,
        "diagnostics": diagnostics,
        "task_type": task_type,
        "user_instruction": user_instruction,
        "use_llm": use_llm,
        "use_rag": use_rag,
        "knowledge_snippets": knowledge_snippets,
    }


def _get_cached_detection_result(signature: str) -> dict | None:
    cached = st.session_state.get("last_detection_result")
    if not cached or cached.get("signature") != signature:
        return None
    return cached


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
        from src.evaluator.report_analyzer import analyze_report_quality, apply_image_precheck_penalties
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

        st.write(f"✓ 文本: {condensation.original_length} → {condensation.condensed_length} 字符 ({_condensation_status(condensation)})")
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
        diagnostics = apply_image_precheck_penalties(diagnostics, img_results)

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

    _render_metric_grid(
        [
            ("文件名", parsed.file_name, ""),
            ("文件类型", parsed.file_type, ""),
            ("原始文本", f"{cond.original_length} 字符", ""),
            ("凝练后", f"{cond.condensed_length} 字符", _condensation_status(cond)),
            ("页数", parsed.page_count or "-", ""),
            ("图片", parsed.image_count, ""),
            ("代码块", f"{len(parsed.code_blocks)} 个", ""),
        ]
    )

    # 关键参数摘要
    if pipeline_result.key_parameters:
        with st.expander("提取的关键技术参数"):
            for cat, vals in pipeline_result.key_parameters.items():
                if vals:
                    st.caption(f"**{cat}**：{', '.join(vals[:10])}")

    tabs = st.tabs(["凝练预览", "原文对比", "格式与图片", "OCR 文本", "预检诊断", "代码块", "表格"])
    with tabs[0]:
        st.caption(f"智能凝练：{cond.original_length} → {cond.condensed_length} 字符；{_condensation_status(cond)}。短文本会保留原文，长文本才会压缩。")
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


def _render_task_config(use_llm: bool) -> tuple[str, str]:
    with st.container(border=True):
        st.subheader("第二步：选择任务与输入需求")
        st.markdown(
            "**这是多任务 Prompt 入口。** 你可以让系统进行全面评阅、专项检查、基于报告问答、生成修改计划或生成教师评语。"
        )
        col_task, col_hint = st.columns([1, 2])
        task_keys = list(TASK_DEFINITIONS.keys())
        with col_task:
            task_type = st.selectbox(
                "任务模式",
                options=task_keys,
                format_func=lambda key: TASK_DEFINITIONS[key]["label"],
                index=0,
                help="不同任务会使用不同 Prompt 模板和不同结果展示方式。",
            )
        with col_hint:
            task_hint = {
                "report_review": "可选：例如“重点看实验结果分析是否充分”。",
                "focused_review": "必填：例如“重点检查 KNN 参数选择是否充分”。",
                "report_qa": "必填：例如“这份报告的事务实验设计是否充分？”。",
                "revision_plan": "可选：例如“优先给出 1 小时内能完成的修改”。",
                "teacher_comment": "可选：例如“评语语气客观一些，适合教师批改”。",
            }[task_type]
            user_instruction = st.text_area(
                "我的需求 / 问题 / 关注点",
                placeholder=task_hint,
                height=120,
                help="这段内容会参与 RAG 检索和大模型 Prompt，但不会覆盖课程 Rubric。",
            ).strip()

        example_cols = st.columns(3)
        examples = [
            ("专项检查", "重点检查 KNN 参数选择和混淆矩阵分析是否充分。"),
            ("报告问答", "这份数据库报告的事务实验是否完整？还缺少哪些证据？"),
            ("修改计划", "帮我按优先级列出最影响得分的修改项。"),
        ]
        for col, (title, example) in zip(example_cols, examples):
            with col:
                st.caption(f"**示例 - {title}**")
                st.code(example, language=None)

        if TASK_DEFINITIONS[task_type]["requires_instruction"]:
            st.warning("当前任务需要填写用户需求；系统会基于上传报告、Rubric 和 RAG 片段回答。")
        elif not user_instruction:
            st.info("未填写额外需求时，系统将按默认任务目标处理。")
        if not use_llm and task_type != "report_review":
            st.info("非全面评阅任务需要启用大模型才能得到对应类型结果；未启用时会回退为规则基础评阅。")

    return task_type, user_instruction


# ── 评阅展示 ────────────────────────────────────────────


def _render_task_result(
    course_result: dict,
    result: dict,
    use_llm: bool,
    diagnostics: dict,
    task_type: str,
    user_instruction: str,
) -> None:
    st.subheader("检测结果")
    _render_task_overview(task_type, user_instruction)

    if "total_score" in result:
        if result.get("focused_conclusion"):
            _render_text_card("针对用户需求的结论", str(result.get("focused_conclusion", "")))
        _render_review(course_result, result, use_llm, diagnostics, show_header=False)
        return

    if task_type == "report_qa":
        _render_report_qa_result(result)
    elif task_type == "revision_plan":
        _render_revision_plan_result(result)
    elif task_type == "teacher_comment":
        _render_teacher_comment_result(result)
    else:
        st.json(result)


def _render_task_overview(task_type: str, user_instruction: str) -> None:
    task_label = TASK_DEFINITIONS[task_type]["label"]
    items = [("任务模式", task_label, "")]
    if user_instruction:
        items.append(("用户需求", user_instruction, ""))
    else:
        items.append(("用户需求", "未填写", "按默认任务目标处理"))
    _render_metric_grid(items)


def _render_report_qa_result(result: dict) -> None:
    tabs = st.tabs(["回答", "依据", "缺失信息", "建议", "引用来源", "原始 JSON"])
    with tabs[0]:
        _render_text_card("回答", str(result.get("answer", "")))
    with tabs[1]:
        _render_bullet_cards("依据", result.get("evidence", []))
    with tabs[2]:
        _render_bullet_cards("缺失信息", result.get("missing_info", []), empty_text="报告中没有明显缺失信息。")
    with tabs[3]:
        _render_bullet_cards("建议", result.get("suggestions", []))
    with tabs[4]:
        _render_bullet_cards("引用来源", result.get("cited_sources", []), empty_text="模型未返回明确引用来源。")
    with tabs[5]:
        st.json(result)


def _render_revision_plan_result(result: dict) -> None:
    _render_summary_card(str(result.get("summary", "")))
    tabs = st.tabs(["优先级修改", "快速修复", "深度改进", "预计收益", "原始 JSON"])
    with tabs[0]:
        actions = result.get("priority_actions", [])
        if not actions:
            st.info("暂无优先级修改项。")
        for index, action in enumerate(actions, start=1):
            if isinstance(action, dict):
                title = f"{index}. [{action.get('priority', '未标注')}] {action.get('target', '修改项')}"
                body = f"动作：{action.get('action', '')}\n\n原因：{action.get('reason', '')}"
            else:
                title = f"{index}. 修改项"
                body = str(action)
            _render_text_card(title, body)
    with tabs[1]:
        _render_bullet_cards("快速修复", result.get("quick_fixes", []))
    with tabs[2]:
        _render_bullet_cards("深度改进", result.get("deep_improvements", []))
    with tabs[3]:
        _render_text_card("预计改进收益", str(result.get("expected_score_gain", "")))
    with tabs[4]:
        st.json(result)


def _render_teacher_comment_result(result: dict) -> None:
    tabs = st.tabs(["教师评语", "优点", "不足", "建议分数", "改进提醒", "原始 JSON"])
    with tabs[0]:
        _render_text_card("教师评语草稿", str(result.get("teacher_comment", "")))
    with tabs[1]:
        _render_bullet_cards("主要优点", result.get("strengths", []))
    with tabs[2]:
        _render_bullet_cards("主要不足", result.get("weaknesses", []))
    with tabs[3]:
        _render_text_card("建议分数或等级区间", str(result.get("score_suggestion", "")))
    with tabs[4]:
        _render_bullet_cards("改进提醒", result.get("improvement_notes", []), empty_text="模型未返回额外改进提醒。")
    with tabs[5]:
        st.json(result)


def _render_bullet_cards(title: str, items, empty_text: str = "暂无内容。") -> None:
    if isinstance(items, str):
        items = [items] if items.strip() else []
    if not items:
        st.info(empty_text)
        return
    for index, item in enumerate(items, start=1):
        _render_text_card(f"{title} {index}", str(item))


def _render_review(course_result: dict, review: dict, use_llm: bool, diagnostics: dict, show_header: bool = True) -> None:
    if show_header:
        st.subheader("检测结果")
    score = int(review["total_score"])
    score_level = _score_level(score)

    _render_metric_grid(
        [
            ("总分", f"{score} / 100", score_level),
            ("课程类型", course_result["course_name"], ""),
            ("问题数量", len(review["problems"]), ""),
            ("评阅方式", "DeepSeek 大模型" if use_llm else "规则占位", ""),
        ]
    )
    st.caption(f"识别理由：{course_result['reason']}")
    st.caption(f"系统预检分：{diagnostics['precheck_score']} / 100；该分数作为辅助诊断，不直接替代模型总分。")
    _render_summary_card(review.get("summary", ""))

    tabs = st.tabs(["分项评分", "问题建议", "教师评语", "风险提示", "原始 JSON"])
    with tabs[0]:
        _render_dimension_score_cards(review.get("dimension_scores", []))

    with tabs[1]:
        if not review["problems"]:
            st.success("未发现明显问题。")
        for index, problem in enumerate(review["problems"], start=1):
            _render_problem_card(index, problem)

    with tabs[2]:
        _render_text_card("教师评语草稿", review.get("teacher_comment", ""))

    with tabs[3]:
        if review["risk_warnings"]:
            for warning in review["risk_warnings"]:
                _render_text_card("风险提示", warning, tag="warning")
        else:
            st.success("未发现明显风险提示。")

    with tabs[4]:
        st.markdown('<div class="json-wrap">', unsafe_allow_html=True)
        st.json(review)
        st.markdown("</div>", unsafe_allow_html=True)


def _render_knowledge_context(snippets: list[dict]) -> None:
    if not snippets:
        st.info("未检索到匹配的本地课程知识库片段。")
        return

    with st.expander("本地课程知识库参考（RAG）", expanded=False):
        st.caption("系统根据课程类型和报告关键词召回以下片段，并在启用大模型评阅时作为参考上下文。")
        for index, item in enumerate(snippets, start=1):
            title = item.get("title", f"知识片段 {index}")
            file_name = item.get("file", "")
            source = item.get("source", file_name)
            score = item.get("score", 0)
            content = item.get("content", "")
            references = item.get("references", [])
            reference_html = ""
            if references:
                reference_items = "".join(
                    f"<li>{_escape_html(str(reference))}</li>" for reference in references[:3]
                )
                reference_html = (
                    '<div class="problem-location">公开参考资料</div>'
                    f'<ul class="card-muted">{reference_items}</ul>'
                )
            _render_html(
                f'<div class="soft-card">'
                f'<div class="score-card-header">'
                f'<div class="score-title">{index}. {_escape_html(title)}</div>'
                f'<span class="tag-pill">匹配分 {score}</span>'
                f'</div>'
                f'<div class="problem-location">本地来源：{_escape_html(source)}</div>'
                f'<p class="card-muted">{_escape_html(content)}</p>'
                f'{reference_html}'
                f'</div>'
            )


def _render_history_sidebar() -> None:
    records = load_history(limit=8)
    with st.expander("最近检测记录", expanded=False):
        if not records:
            st.caption("暂无历史记录。完成一次检测后会自动记录摘要。")
            return
        rows = [
            {
                "时间": item.get("timestamp", ""),
                "文件": item.get("file_name", ""),
                "课程": item.get("course_name", ""),
                "任务": item.get("task_label", item.get("task_type", "")),
                "分数": item.get("total_score", ""),
                "问题": item.get("problem_count", ""),
                "LLM": "是" if item.get("use_llm") else "否",
                "RAG": "是" if item.get("use_rag") else "否",
            }
            for item in records
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_feedback_section(
    file_name: str,
    course_result: dict,
    result: dict,
    task_type: str,
    user_instruction: str,
    use_llm: bool,
    use_rag: bool,
    knowledge_snippets: list[dict],
) -> None:
    with st.container(border=True):
        st.subheader("用户反馈 / 学习记录")
        st.caption("记录本次检测结果是否有帮助，以及你准备如何修改报告。记录只保存在本地 outputs/feedback.jsonl。")

        form_key = f"feedback_{file_name}_{task_type}_{result.get('total_score', '')}_{len(result.get('problems', []))}"
        with st.form(form_key):
            col_help, col_action = st.columns(2)
            with col_help:
                helpfulness = st.radio(
                    "本次反馈是否有帮助？",
                    ["有帮助", "部分有帮助", "不准确"],
                    horizontal=True,
                )
            with col_action:
                adoption = st.radio(
                    "你准备如何处理这些建议？",
                    ["准备修改", "已采纳", "暂不采纳"],
                    horizontal=True,
                )
            weak_points = st.multiselect(
                "本次主要薄弱点",
                ["报告结构", "实验结果", "结果分析", "代码说明", "图表/截图", "课程知识点", "格式规范", "其他"],
                help="用于形成简单学习记录，可多选。",
            )
            note = st.text_area(
                "备注 / 后续修改计划",
                placeholder="例如：先补充不同 k 值对比表，再完善混淆矩阵分析。",
                height=90,
            ).strip()
            submitted = st.form_submit_button("保存反馈记录", use_container_width=True)

        if submitted:
            feedback_record = {
                "file_name": file_name,
                "course_type": course_result.get("course_type", ""),
                "course_name": course_result.get("course_name", ""),
                "task_type": task_type,
                "task_label": TASK_DEFINITIONS[task_type]["label"],
                "user_instruction": user_instruction,
                "result_summary": _extract_result_summary(result, task_type),
                "total_score": result.get("total_score"),
                "problem_count": len(result.get("problems", [])),
                "helpfulness": helpfulness,
                "adoption": adoption,
                "weak_points": weak_points,
                "note": note,
                "use_llm": use_llm,
                "use_rag": use_rag,
                "rag_sources": [item.get("source", "") for item in knowledge_snippets],
            }
            signature = "|".join(
                [
                    file_name,
                    task_type,
                    helpfulness,
                    adoption,
                    ",".join(weak_points),
                    note,
                ]
            )
            if st.session_state.get("last_feedback_signature") == signature:
                st.info("这条反馈已经保存过，本次未重复写入。")
            else:
                append_feedback_record(feedback_record)
                st.session_state["last_feedback_signature"] = signature
                st.success("反馈已保存到本地学习记录。")

        recent_feedback = load_feedback(limit=5)
        with st.expander("查看最近反馈记录", expanded=False):
            if not recent_feedback:
                st.caption("暂无反馈记录。")
            else:
                rows = [
                    {
                        "时间": item.get("timestamp", ""),
                        "文件": item.get("file_name", ""),
                        "任务": item.get("task_label", item.get("task_type", "")),
                        "帮助度": item.get("helpfulness", ""),
                        "处理": item.get("adoption", ""),
                        "薄弱点": "、".join(item.get("weak_points", [])),
                        "备注 / 后续修改计划": item.get("note", ""),
                    }
                    for item in recent_feedback
                ]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _save_detection_history(
    file_name: str,
    course_result: dict,
    review: dict,
    use_llm: bool,
    use_rag: bool,
    knowledge_snippets: list[dict],
    task_type: str = "report_review",
    user_instruction: str = "",
) -> None:
    signature = "|".join(
        [
            file_name,
            str(course_result.get("course_type", "")),
            task_type,
            user_instruction,
            str(review.get("total_score", "")),
            str(len(review.get("problems", []))),
            str(use_llm),
            str(use_rag),
            ",".join(item.get("source", "") for item in knowledge_snippets),
        ]
    )
    if st.session_state.get("last_history_signature") == signature:
        return

    append_history_record(
        {
            "file_name": file_name,
            "course_type": course_result.get("course_type", ""),
            "course_name": course_result.get("course_name", ""),
            "task_type": task_type,
            "task_label": TASK_DEFINITIONS[task_type]["label"],
            "user_instruction": user_instruction,
            "result_summary": _extract_result_summary(review, task_type),
            "total_score": review.get("total_score", 0),
            "problem_count": len(review.get("problems", [])),
            "use_llm": use_llm,
            "use_rag": use_rag,
            "rag_sources": [item.get("source", "") for item in knowledge_snippets],
        }
    )
    st.session_state["last_history_signature"] = signature


def _extract_result_summary(result: dict, task_type: str) -> str:
    if result.get("summary"):
        return str(result["summary"])
    if task_type == "report_qa":
        return str(result.get("answer", ""))[:120]
    if task_type == "teacher_comment":
        return str(result.get("teacher_comment", ""))[:120]
    return TASK_DEFINITIONS[task_type]["label"]


def _render_summary_card(summary: str) -> None:
    if not summary:
        return
    _render_html(
        f'<div class="summary-card"><strong>总体评价：</strong>{_escape_html(summary)}</div>',
    )


def _render_dimension_score_cards(items: list[dict]) -> None:
    if not items:
        st.info("暂无分项评分。")
        return

    for item in items:
        dimension = str(item.get("dimension", "未命名维度"))
        score = _safe_float(item.get("score", 0))
        max_score = max(1.0, _safe_float(item.get("max_score", 100)))
        percent = max(0, min(100, score / max_score * 100))
        comment = str(item.get("comment", ""))
        _render_html(
            f'<div class="soft-card">'
            f'<div class="score-card-header">'
            f'<div class="score-title">{_escape_html(dimension)}</div>'
            f'<span class="score-pill">{score:g} / {max_score:g}</span>'
            f'</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width: {percent:.1f}%"></div></div>'
            f'<p class="card-muted">{_escape_html(comment)}</p>'
            f'</div>'
        )


def _render_problem_card(index: int, problem: dict) -> None:
    problem_type = str(problem.get("type", "问题"))
    location = str(problem.get("location", "未标注"))
    description = str(problem.get("description", ""))
    suggestion = str(problem.get("suggestion", ""))
    _render_html(
        f'<div class="soft-card">'
        f'<div class="problem-card-header">'
        f'<div class="problem-title">{index}. {_escape_html(problem_type)}</div>'
        f'<span class="tag-pill">问题建议</span>'
        f'</div>'
        f'<div class="problem-location">位置：{_escape_html(location)}</div>'
        f'<p class="card-muted">{_escape_html(description)}</p>'
        f'<div class="suggestion-box"><strong>修改建议：</strong>{_escape_html(suggestion)}</div>'
        f'</div>'
    )


def _render_text_card(title: str, body: str, tag: str = "info") -> None:
    if not body:
        st.info("暂无内容。")
        return
    tag_text = "提示" if tag == "warning" else "文本"
    _render_html(
        f'<div class="soft-card">'
        f'<div class="score-card-header">'
        f'<div class="score-title">{_escape_html(title)}</div>'
        f'<span class="tag-pill">{tag_text}</span>'
        f'</div>'
        f'<p class="card-muted">{_escape_html(body)}</p>'
        f'</div>'
    )


def _render_metric_grid(items: list[tuple[str, object, object]]) -> None:
    cards = []
    for label, value, delta in items:
        delta_html = f'<div class="metric-delta">{_escape_html(delta)}</div>' if delta not in ("", None) else ""
        cards.append(
            f'<div class="metric-card">'
            f'<div class="metric-label">{_escape_html(label)}</div>'
            f'<div class="metric-value">{_escape_html(value)}</div>'
            f'{delta_html}'
            f'</div>'
        )
    _render_html('<div class="metric-grid">' + "".join(cards) + "</div>")


def _render_html(markup: str) -> None:
    if hasattr(st, "html"):
        st.html(markup)
    else:
        st.markdown(markup, unsafe_allow_html=True)


def _escape_html(value) -> str:
    return html.escape(str(value)).replace("\n", "<br>")


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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


def _condensation_status(cond) -> str:
    original = max(1, int(cond.original_length))
    condensed = int(cond.condensed_length)
    if condensed >= original:
        return "无需压缩"
    reduction = max(0, round((1 - condensed / original) * 100))
    return f"精简 {reduction}%"


if __name__ == "__main__":
    main()
