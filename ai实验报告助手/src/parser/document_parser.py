from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

import fitz
from docx import Document


@dataclass
class ParsedReport:
    file_name: str
    file_type: str
    full_text: str
    code_blocks: list[str]
    tables: list[str]


def parse_uploaded_file(uploaded_file) -> ParsedReport:
    suffix = Path(uploaded_file.name).suffix.lower().lstrip(".")
    content = uploaded_file.getvalue()

    if suffix == "docx":
        text, tables = _parse_docx(content)
    elif suffix == "pdf":
        text, tables = _parse_pdf(content), []
    elif suffix in {"txt", "md"}:
        text, tables = content.decode("utf-8", errors="ignore"), []
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    return ParsedReport(
        file_name=uploaded_file.name,
        file_type=suffix,
        full_text=text.strip(),
        code_blocks=_extract_simple_code_blocks(text),
        tables=tables,
    )


def _parse_docx(content: bytes) -> tuple[str, list[str]]:
    with NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    document = Document(tmp_path)
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]

    tables = []
    for table in document.tables:
        rows = []
        for row in table.rows:
            cells = [" ".join(cell.text.split()) for cell in row.cells]
            rows.append(" | ".join(cells))
        tables.append("\n".join(rows))

    text_parts = paragraphs + tables
    return "\n\n".join(text_parts), tables


def _parse_pdf(content: bytes) -> str:
    with fitz.open(stream=content, filetype="pdf") as document:
        pages = [page.get_text("text") for page in document]
    return "\n\n".join(pages)


def _extract_simple_code_blocks(text: str) -> list[str]:
    blocks = []
    current = []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_block and current:
                blocks.append("\n".join(current))
                current = []
            in_block = not in_block
            continue
        if in_block:
            current.append(line)
    return blocks
