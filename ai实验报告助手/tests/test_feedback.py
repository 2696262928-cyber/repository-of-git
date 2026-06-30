from pathlib import Path

from src.utils.feedback import append_feedback_record, load_feedback


def test_feedback_jsonl_roundtrip(tmp_path: Path):
    feedback_path = tmp_path / "feedback.jsonl"

    append_feedback_record(
        {
            "file_name": "ai_knn_report.md",
            "task_type": "focused_review",
            "helpfulness": "有帮助",
            "adoption": "准备修改",
            "weak_points": ["结果分析", "课程知识点"],
        },
        path=feedback_path,
    )
    records = load_feedback(limit=5, path=feedback_path)

    assert len(records) == 1
    assert records[0]["file_name"] == "ai_knn_report.md"
    assert records[0]["helpfulness"] == "有帮助"
    assert records[0]["adoption"] == "准备修改"
    assert records[0]["weak_points"] == ["结果分析", "课程知识点"]
    assert "timestamp" in records[0]


def test_load_feedback_handles_missing_or_invalid_file(tmp_path: Path):
    missing_path = tmp_path / "missing.jsonl"
    assert load_feedback(path=missing_path) == []

    invalid_path = tmp_path / "feedback.jsonl"
    invalid_path.write_text("{bad json}\n{\"file_name\":\"ok.md\"}\n", encoding="utf-8")
    records = load_feedback(path=invalid_path)

    assert len(records) == 1
    assert records[0]["file_name"] == "ok.md"
