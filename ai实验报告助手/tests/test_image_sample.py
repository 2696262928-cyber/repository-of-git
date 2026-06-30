from pathlib import Path

from src.parser.document_parser import parse_uploaded_file


class LocalUpload:
    def __init__(self, path: Path):
        self.name = path.name
        self._content = path.read_bytes()

    def getvalue(self):
        return self._content


def test_docx_image_sample_has_embedded_image():
    sample = Path("data/samples/programming_with_image_report.docx")
    parsed = parse_uploaded_file(LocalUpload(sample))

    assert parsed.file_type == "docx"
    assert parsed.image_count >= 1
    assert "排序算法性能比较" in parsed.full_text

