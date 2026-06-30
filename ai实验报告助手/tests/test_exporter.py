from src.exporter.report_exporter import export_docx_review, export_markdown_review


def _review():
    return {
        "summary": "整体结构基本完整。",
        "total_score": 88,
        "dimension_scores": [
            {"dimension": "结构完整性", "score": 18, "max_score": 20, "comment": "章节齐全。"}
        ],
        "problems": [
            {"type": "结果分析", "location": "结果分析", "description": "分析偏少。", "suggestion": "补充原因解释。"}
        ],
        "teacher_comment": "报告完成度较好。",
        "risk_warnings": [],
    }


def test_export_markdown_includes_knowledge_snippets():
    markdown = export_markdown_review(
        "sample.md",
        {"course_name": "数据结构与算法"},
        _review(),
        [
            {
                "title": "栈",
                "source": "data_structure.md#栈",
                "score": 3.2,
                "matched_keywords": ["栈"],
                "content": "栈是后进先出结构。",
                "references": ["OpenDSA: https://opendsa-server.cs.vt.edu/ODSA/Books/Everything/html/"],
            }
        ],
    )

    assert "本地课程知识库引用" in markdown
    assert "data_structure.md#栈" in markdown
    assert "公开参考" in markdown
    assert "OpenDSA" in markdown
    assert "任务模式" in markdown


def test_export_docx_returns_bytes():
    payload = export_docx_review("sample.md", {"course_name": "数据结构与算法"}, _review())

    assert payload.startswith(b"PK")
    assert len(payload) > 1000


def test_export_markdown_includes_user_instruction_for_qa_task():
    result = {
        "answer": "事务实验过程不够充分。",
        "evidence": ["报告只展示单会话 SQL。"],
        "missing_info": ["缺少并发会话对比。"],
        "suggestions": ["补充两个会话的事务隔离实验。"],
        "cited_sources": ["database.md#事务、隔离级别与并发现象"],
    }
    markdown = export_markdown_review(
        "database.md",
        {"course_name": "数据库"},
        result,
        task_type="report_qa",
        user_instruction="事务实验设计是否充分？",
    )

    assert "基于报告问答" in markdown
    assert "事务实验设计是否充分？" in markdown
    assert "事务实验过程不够充分" in markdown
