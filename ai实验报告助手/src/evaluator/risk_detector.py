def detect_basic_risks(report_text: str) -> list[str]:
    risks = []
    if len(report_text) < 1200:
        risks.append("报告正文较短，可能缺少实验过程或结果分析。")
    if "参考" not in report_text and "引用" not in report_text:
        risks.append("未发现参考资料或引用说明。")
    if "运行结果" not in report_text and "实验结果" not in report_text:
        risks.append("未发现明确的运行结果章节。")
    return risks
