from datetime import datetime


def export_markdown_review(file_name: str, course_result: dict, review: dict) -> str:
    lines = [
        "# 实验报告检测结果",
        "",
        "## 基本信息",
        "",
        f"- 文件名：{file_name}",
        f"- 课程类型：{course_result['course_name']}",
        f"- 检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 总体评分",
        "",
        f"- 总分：{review['total_score']} / 100",
        f"- 总评：{review['summary']}",
        "",
        "## 分项评分",
        "",
        "| 维度 | 得分 | 满分 | 说明 |",
        "| --- | ---: | ---: | --- |",
    ]
    for item in review["dimension_scores"]:
        lines.append(
            f"| {item['dimension']} | {item['score']} | {item['max_score']} | {item['comment']} |"
        )

    lines.extend(["", "## 主要问题与修改建议", ""])
    for index, problem in enumerate(review["problems"], start=1):
        lines.extend(
            [
                f"### {index}. {problem['type']}",
                "",
                f"- 位置：{problem['location']}",
                f"- 问题：{problem['description']}",
                f"- 建议：{problem['suggestion']}",
                "",
            ]
        )

    lines.extend(["## 教师评语草稿", "", review["teacher_comment"], "", "## 风险提示", ""])
    if review["risk_warnings"]:
        for warning in review["risk_warnings"]:
            lines.append(f"- {warning}")
    else:
        lines.append("- 未发现明显风险提示。")
    return "\n".join(lines)
