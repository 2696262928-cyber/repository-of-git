from pathlib import Path

import streamlit as st

from src.classifier.course_classifier import classify_course_by_rules
from src.evaluator.rubric_loader import list_rubrics, load_rubric
from src.exporter.report_exporter import export_markdown_review
from src.parser.document_parser import parse_uploaded_file


st.set_page_config(
    page_title="实验报告智能检测与反馈系统",
    page_icon="",
    layout="wide",
)


def main() -> None:
    st.title("面向计算机类课程的实验报告智能检测与反馈系统")
    st.caption("上传实验报告，系统将解析内容、匹配评分标准，并生成检测反馈。")

    rubrics = list_rubrics()
    course_options = {"auto": "自动识别"}
    course_options.update({item["course_type"]: item["course_name"] for item in rubrics})

    with st.sidebar:
        st.header("检测设置")
        uploaded_file = st.file_uploader(
            "上传实验报告",
            type=["docx", "pdf", "txt", "md"],
        )
        selected_course = st.selectbox(
            "课程类型",
            options=list(course_options.keys()),
            format_func=lambda key: course_options[key],
        )
        use_llm = st.checkbox("启用大模型评阅", value=False)
        st.caption("当前骨架默认使用规则与占位反馈。完成 LLM 接入后可开启真实评阅。")
        start = st.button("开始检测", type="primary", use_container_width=True)

    if not uploaded_file:
        st.info("请先上传一份 DOCX、PDF、TXT 或 Markdown 格式的实验报告。")
        return

    parsed = parse_uploaded_file(uploaded_file)

    left, right = st.columns([1, 1])
    with left:
        st.subheader("解析预览")
        st.write(f"文件名：`{parsed.file_name}`")
        st.write(f"文件类型：`{parsed.file_type}`")
        st.write(f"文本长度：`{len(parsed.full_text)}` 字符")
        st.text_area("报告正文预览", parsed.full_text[:5000], height=360)

    if not start:
        with right:
            st.subheader("等待检测")
            st.write("确认解析内容无误后，点击左侧“开始检测”。")
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
    review = build_placeholder_review(parsed.full_text, rubric, course_result, use_llm)

    with right:
        st.subheader("检测结果")
        st.metric("总分", f"{review['total_score']} / 100")
        st.write(f"课程类型：`{course_result['course_name']}`")
        st.write(f"识别理由：{course_result['reason']}")

    st.subheader("分项评分")
    st.dataframe(review["dimension_scores"], use_container_width=True)

    st.subheader("主要问题与修改建议")
    for problem in review["problems"]:
        st.markdown(f"**{problem['type']}** - {problem['location']}")
        st.write(problem["description"])
        st.info(problem["suggestion"])

    st.subheader("教师评语草稿")
    st.write(review["teacher_comment"])

    st.subheader("风险提示")
    if review["risk_warnings"]:
        for warning in review["risk_warnings"]:
            st.warning(warning)
    else:
        st.success("未发现明显风险提示。")

    markdown = export_markdown_review(parsed.file_name, course_result, review)
    st.download_button(
        "下载 Markdown 检测报告",
        data=markdown,
        file_name=f"{Path(parsed.file_name).stem}_检测报告.md",
        mime="text/markdown",
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


if __name__ == "__main__":
    main()
