import pytest

from src.evaluator.llm_evaluator import (
    TASK_DEFINITIONS,
    build_prompt,
    build_task_rag_query,
    get_prompt_template_path,
    validate_task_result,
)


def test_all_task_prompt_files_exist():
    for task_type in TASK_DEFINITIONS:
        assert get_prompt_template_path(task_type).exists()


def test_build_prompt_includes_user_instruction_and_rag_context():
    template = "任务={task_type}\n需求={user_instruction}\n知识={knowledge_context}\n报告={report_text}\n标准={rubric}\n诊断={diagnostics}"
    prompt = build_prompt(
        template,
        report_text="报告正文",
        rubric={"dimensions": []},
        diagnostics={"precheck_score": 80},
        knowledge_context="KNN 参考片段",
        task_type="focused_review",
        user_instruction="重点检查 KNN 参数选择",
    )

    assert "按需求重点检查" in prompt
    assert "重点检查 KNN 参数选择" in prompt
    assert "KNN 参考片段" in prompt
    assert "precheck_score" in prompt


def test_build_task_rag_query_combines_report_task_and_user_instruction():
    query = build_task_rag_query("报告正文", "report_qa", "事务实验设计是否充分？")

    assert "报告正文" in query
    assert "基于报告问答" in query
    assert "事务实验设计是否充分？" in query


def test_validate_task_result_accepts_report_qa_schema():
    validate_task_result(
        {
            "answer": "报告中参数分析不足。",
            "evidence": ["报告只给出 k=5。"],
            "missing_info": ["缺少不同 k 值对比。"],
            "suggestions": ["补充 k 值实验表。"],
            "cited_sources": ["ai_ml.md#KNN、距离度量与特征缩放"],
        },
        "report_qa",
    )


def test_validate_task_result_rejects_missing_fields():
    with pytest.raises(Exception):
        validate_task_result({"answer": "缺少字段"}, "report_qa")
