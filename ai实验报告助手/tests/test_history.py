from pathlib import Path

from src.utils.history import append_history_record, load_history


def test_history_jsonl_roundtrip(tmp_path: Path):
    history_path = tmp_path / "history.jsonl"

    append_history_record({"file_name": "a.md", "total_score": 80}, path=history_path)
    append_history_record(
        {
            "file_name": "b.md",
            "total_score": 90,
            "task_type": "focused_review",
            "user_instruction": "重点检查结果分析",
        },
        path=history_path,
    )
    records = load_history(limit=1, path=history_path)

    assert len(records) == 1
    assert records[0]["file_name"] == "b.md"
    assert records[0]["total_score"] == 90
    assert records[0]["task_type"] == "focused_review"
    assert records[0]["user_instruction"] == "重点检查结果分析"
    assert "timestamp" in records[0]
