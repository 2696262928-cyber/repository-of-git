from pathlib import Path

import pandas as pd
import streamlit as st

from src.classifier.course_classifier import classify_course_by_rules
from src.evaluator.llm_evaluator import LLMEvaluationError, evaluate_with_openai_compatible_api
from src.evaluator.rubric_loader import list_rubrics, load_rubric
from src.exporter.report_exporter import export_markdown_review
from src.parser.document_parser import parse_uploaded_file
from src.utils.settings import load_settings


st.set_page_config(
    page_title="实验报告智能检测与反馈系统",
    page_icon="",
    layout="wide",
)


def main() -> None:
    st.title("面向计算机类课程的实验报告智能检测与反馈系统")
    st.caption("上传实验报告，系统将解析内容、匹配评分标准，并生成检测反馈。")
    st.caption("当前版本：LLM 接入修复版 v2")

    rubrics = list_rubrics()
    course_options = {"auto": "自动识别"}
    course_options.update({item["course_type"]: item["course_name"] for item in rubrics})
    settings = load_settings()
    llm_ready = _is_llm_configured(settings)

    with st.sidebar:
        st.header("检测设置")
        st.progress(0.2, text="第 1 步：上传报告")
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
        st.progress(0.45, text="第 2 步：选择评阅方式")
        use_llm = st.checkbox("启用大模型评阅", value=False)
        if llm_ready:
            st.success(f"模型配置：{settings['llm']['model']}")
        else:
            st.warning("尚未填写 DeepSeek API Key，可先使用规则检测。")
        st.caption("勾选后将读取 config/settings.json 并调用 OpenAI-compatible 模型接口。")
        st.progress(0.7, text="第 3 步：开始检测")
        start = st.button("开始检测", type="primary", use_container_width=True)

    if not uploaded_file:
        _render_empty_state(course_options)
        return

    parsed = parse_uploaded_file(uploaded_file)

    _render_parsed_summary(parsed)

    if not start:
        st.info("确认解析内容无误后，点击左侧“开始检测”。")
        return

    if selected_course == "auto":
        course_result = classify_course_by_rules(parsed.full_text)
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
    if use_llm:
        try:
            max_chars = settings.get("app", {}).get("max_report_chars", 20000)
            prompt_template = Path("prompts/report_review_prompt.txt").read_text(encoding="utf-8")
            with st.spinner("正在调用大模型评阅，请稍候..."):
                review = evaluate_with_openai_compatible_api(
                    parsed.full_text[:max_chars],
                    rubric,
                    settings,
                    prompt_template,
                )
        except (FileNotFoundError, KeyError, ValueError, LLMEvaluationError) as exc:
            st.error(f"大模型评阅失败：{exc}")
            st.info("请检查 config/settings.json 中的 base_url、api_key 和 model 配置，或先关闭“大模型评阅”使用规则占位检测。")
            return
    else:
        review = build_placeholder_review(parsed.full_text, rubric, course_result, use_llm)

    _render_review(course_result, review, use_llm)

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


def build_placeholder_review(report_text: str, rubric: dict, course_result: dict, use_llm: bool) -> dict:
    """Temporary review output before the LLM evaluator is implemented."""
    missing_sections = []
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


def _render_parsed_summary(parsed) -> None:
    st.subheader("解析预览")
    cols = st.columns(4)
    cols[0].metric("文件名", parsed.file_name)
    cols[1].metric("文件类型", parsed.file_type)
    cols[2].metric("文本长度", f"{len(parsed.full_text)} 字符")
    cols[3].metric("代码块", f"{len(parsed.code_blocks)} 个")

    tabs = st.tabs(["正文预览", "代码块", "表格"])
    with tabs[0]:
        st.text_area("报告正文预览", parsed.full_text[:5000], height=320)
    with tabs[1]:
        if parsed.code_blocks:
            for index, code in enumerate(parsed.code_blocks, start=1):
                st.code(code, language="python")
                st.caption(f"代码块 {index}")
        else:
            st.info("未识别到 Markdown 代码块。DOCX/PDF 的代码提取将在后续版本继续增强。")
    with tabs[2]:
        if parsed.tables:
            for index, table in enumerate(parsed.tables, start=1):
                st.text_area(f"表格 {index}", table, height=160)
        else:
            st.info("未识别到表格。")


def _render_review(course_result: dict, review: dict, use_llm: bool) -> None:
    st.subheader("检测结果")
    score = int(review["total_score"])
    score_level = _score_level(score)

    cols = st.columns(4)
    cols[0].metric("总分", f"{score} / 100", score_level)
    cols[1].metric("课程类型", course_result["course_name"])
    cols[2].metric("问题数量", len(review["problems"]))
    cols[3].metric("评阅方式", "DeepSeek 大模型" if use_llm else "规则占位")
    st.progress(score / 100, text=f"综合得分：{score} / 100")
    st.caption(f"识别理由：{course_result['reason']}")

    tabs = st.tabs(["分项评分", "问题建议", "教师评语", "风险提示", "原始 JSON"])
    with tabs[0]:
        df = pd.DataFrame(review["dimension_scores"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        for item in review["dimension_scores"]:
            score_ratio = item["score"] / item["max_score"] if item["max_score"] else 0
            st.progress(score_ratio, text=f"{item['dimension']}：{item['score']} / {item['max_score']}")

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
