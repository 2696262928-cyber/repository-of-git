from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "data" / "knowledge_base"

COURSE_KNOWLEDGE_FILES = {
    "programming": "programming.md",
    "data_structure": "data_structure.md",
    "database": "database.md",
    "operating_system": "operating_system.md",
    "computer_network": "computer_network.md",
    "ai_ml": "ai_ml.md",
    "embedded_system": "embedded_system.md",
}

STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "are", "was", "were",
    "实验", "报告", "结果", "分析", "代码", "步骤", "目的", "总结", "环境",
    "系统", "进行", "说明", "通过", "需要", "使用", "可以", "应该",
}


@dataclass(frozen=True)
class KnowledgeChunk:
    course_type: str
    file: str
    title: str
    content: str
    references: tuple[str, ...]
    preferred: bool
    index: int


def retrieve_knowledge(report_text: str, course_type: str, top_k: int = 3, max_chars: int = 1200) -> list[dict]:
    """Retrieve course knowledge with a lightweight BM25 scorer.

    Returns dictionaries for UI/export compatibility:
    `course_type`, `file`, `title`, `content`, `score`, `matched_keywords`,
    `source`, `preferred`.
    """
    if top_k <= 0 or max_chars <= 0:
        return []

    query_terms = _tokenize(report_text)
    if not query_terms:
        return []

    chunks = _load_all_chunks(course_type)
    if not chunks:
        return []

    scored = _score_chunks_bm25(chunks, query_terms)
    if not scored:
        return []

    return _limit_snippets(scored[:top_k], max_chars)


def format_knowledge_for_prompt(snippets: list[dict]) -> str:
    """Format retrieved snippets as a separate RAG prompt field."""
    if not snippets:
        return "未检索到可用的本地课程知识库片段。"

    blocks = []
    for index, item in enumerate(snippets, start=1):
        title = item.get("title") or item.get("file") or f"知识片段 {index}"
        source = item.get("source") or item.get("file", "unknown")
        keywords = "、".join(item.get("matched_keywords", [])[:8]) or "无"
        references = _format_references(item.get("references", []), limit=2)
        content = str(item.get("content", "")).strip()
        blocks.append(
            f"[{index}] {title}\n"
            f"来源：{source}\n"
            f"公开参考：{references}\n"
            f"匹配关键词：{keywords}\n"
            f"内容：{content}"
        )
    return "\n\n".join(blocks)


def _load_all_chunks(course_type: str) -> list[KnowledgeChunk]:
    preferred_name = COURSE_KNOWLEDGE_FILES.get(course_type)
    all_files = sorted(KNOWLEDGE_BASE_DIR.glob("*.md"))
    chunks: list[KnowledgeChunk] = []
    for path in all_files:
        preferred = path.name == preferred_name
        chunks.extend(_load_file_chunks(path, preferred))
    return chunks


def _load_file_chunks(file_path: Path, preferred: bool) -> list[KnowledgeChunk]:
    if not file_path.exists():
        return []

    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    references = _extract_references(text)
    chunks = []
    parts = re.split(r"\n(?=##\s+)", text)
    for index, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue

        lines = part.splitlines()
        title = lines[0].lstrip("#").strip() if lines else file_path.stem
        if title == "参考来源":
            continue

        content = "\n".join(lines[1:]).strip() if len(lines) > 1 else part
        if not content:
            continue

        chunks.append(
            KnowledgeChunk(
                course_type=_course_type_from_file(file_path),
                file=file_path.name,
                title=title,
                content=content,
                references=references,
                preferred=preferred,
                index=index,
            )
        )
    return chunks


def _score_chunks_bm25(chunks: list[KnowledgeChunk], query_terms: set[str]) -> list[dict]:
    tokenized_docs = [_tokenize_list(chunk.title + "\n" + chunk.content) for chunk in chunks]
    doc_lengths = [len(tokens) for tokens in tokenized_docs]
    avg_doc_len = sum(doc_lengths) / max(1, len(doc_lengths))
    doc_freq: Counter[str] = Counter()
    for tokens in tokenized_docs:
        doc_freq.update(set(tokens))

    scored = []
    for chunk, tokens, doc_len in zip(chunks, tokenized_docs, doc_lengths):
        if not tokens:
            continue
        term_freq = Counter(tokens)
        matched = sorted(query_terms & set(tokens))
        if not matched:
            continue

        score = _bm25_score(matched, term_freq, doc_freq, len(chunks), doc_len, avg_doc_len)
        if chunk.preferred:
            score *= 1.35
            score += 1.0

        scored.append(
            {
                "course_type": chunk.course_type,
                "file": chunk.file,
                "title": chunk.title,
                "content": chunk.content,
                "references": list(chunk.references),
                "preferred": chunk.preferred,
                "score": round(score, 4),
                "matched_keywords": matched[:12],
                "source": f"{chunk.file}#{chunk.title}",
                "chunk_index": chunk.index,
            }
        )

    scored.sort(key=lambda item: (-item["score"], 0 if item["preferred"] else 1, item["source"]))
    return scored


def _bm25_score(
    matched_terms: list[str],
    term_freq: Counter[str],
    doc_freq: Counter[str],
    doc_count: int,
    doc_len: int,
    avg_doc_len: float,
) -> float:
    k1 = 1.5
    b = 0.75
    score = 0.0
    for term in matched_terms:
        tf = term_freq[term]
        df = doc_freq[term]
        idf = math.log(1 + (doc_count - df + 0.5) / (df + 0.5))
        denom = tf + k1 * (1 - b + b * doc_len / max(1.0, avg_doc_len))
        score += idf * (tf * (k1 + 1)) / denom
    return score


def _tokenize(text: str) -> set[str]:
    return set(_tokenize_list(text))


def _tokenize_list(text: str) -> list[str]:
    lowered = text.lower()
    terms = re.findall(r"[a-z][a-z0-9_+#.-]{1,}|[0-9]+(?:\.[0-9]+)?", lowered)

    for segment in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        terms.extend(segment[i:i + 2] for i in range(max(0, len(segment) - 1)))
        terms.extend(segment[i:i + 3] for i in range(max(0, len(segment) - 2)))

    return [term for term in terms if term not in STOPWORDS and len(term.strip()) >= 2]


def _limit_snippets(snippets: list[dict], max_chars: int) -> list[dict]:
    remaining = max_chars
    limited = []
    for item in snippets:
        content = str(item["content"]).strip()
        if remaining <= 0:
            break
        if len(content) > remaining:
            if remaining <= 3:
                content = content[:remaining]
            else:
                content = content[: remaining - 3].rstrip() + "..."
        limited.append({**item, "content": content})
        remaining -= len(content)
    return limited


def _extract_references(text: str) -> tuple[str, ...]:
    match = re.search(r"\n##\s+参考来源\s*\n(?P<body>.*?)(?=\n##\s+|\Z)", text, re.S)
    if not match:
        return ()

    references = []
    for line in match.group("body").splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        item = line.lstrip("-").strip()
        if item:
            references.append(item)
    return tuple(references)


def _format_references(references: list[str] | tuple[str, ...], limit: int = 2) -> str:
    if not references:
        return "无"
    return "；".join(str(item) for item in references[:limit])


def _course_type_from_file(file_path: Path) -> str:
    for course_type, file_name in COURSE_KNOWLEDGE_FILES.items():
        if file_path.name == file_name:
            return course_type
    return "unknown"
