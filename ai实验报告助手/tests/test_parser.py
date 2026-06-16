from src.parser.code_extractor import extract_code_like_lines


def test_extract_code_like_lines():
    text = "说明\nimport os\ndef main():\n结束"
    lines = extract_code_like_lines(text)
    assert "import os" in lines
    assert "def main():" in lines
