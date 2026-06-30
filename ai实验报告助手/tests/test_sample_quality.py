from pathlib import Path

from src.classifier.course_classifier import classify_course_by_rules
from src.retriever.simple_retriever import retrieve_knowledge


SAMPLES_DIR = Path("data/samples")


def test_enhanced_samples_are_present_and_nontrivial():
    expected_min_lengths = {
        "ai_knn_report.md": 3000,
        "database_sql_report.md": 4000,
        "bad_ai_only_accuracy_report.md": 600,
        "bad_network_screenshot_only_report.md": 600,
    }

    for file_name, min_length in expected_min_lengths.items():
        text = (SAMPLES_DIR / file_name).read_text(encoding="utf-8")
        assert len(text) >= min_length


def test_enhanced_samples_classify_and_retrieve_expected_courses():
    expected_courses = {
        "ai_knn_report.md": "ai_ml",
        "database_sql_report.md": "database",
        "bad_ai_only_accuracy_report.md": "ai_ml",
        "bad_network_screenshot_only_report.md": "computer_network",
    }

    for file_name, expected_course in expected_courses.items():
        text = (SAMPLES_DIR / file_name).read_text(encoding="utf-8")
        result = classify_course_by_rules(text)
        snippets = retrieve_knowledge(text, result["course_type"], top_k=3, max_chars=1200)

        assert result["course_type"] == expected_course
        assert snippets
