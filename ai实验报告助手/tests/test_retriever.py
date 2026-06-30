from src.retriever.simple_retriever import format_knowledge_for_prompt, retrieve_knowledge


def test_retrieve_knowledge_uses_course_file():
    snippets = retrieve_knowledge("KNN 鸢尾花 分类 准确率 混淆矩阵", "ai_ml", top_k=3, max_chars=1200)

    assert snippets
    assert snippets[0]["course_type"] == "ai_ml"
    assert snippets[0]["file"] == "ai_ml.md"


def test_retrieve_knowledge_respects_top_k():
    snippets = retrieve_knowledge("SQL 主键 外键 查询 事务 索引", "database", top_k=2, max_chars=1200)

    assert 0 < len(snippets) <= 2


def test_retrieve_knowledge_unknown_course_does_not_fail():
    snippets = retrieve_knowledge("TCP HTTP DNS 抓包 端口", "unknown", top_k=3, max_chars=1200)

    assert isinstance(snippets, list)


def test_retrieve_knowledge_respects_max_chars():
    max_chars = 120
    snippets = retrieve_knowledge("进程 线程 调度 时间片 周转时间", "operating_system", top_k=3, max_chars=max_chars)
    total_chars = sum(len(item["content"]) for item in snippets)

    assert total_chars <= max_chars


def test_retrieve_knowledge_includes_public_references():
    snippets = retrieve_knowledge("KNN 鸢尾花 分类 准确率 混淆矩阵", "ai_ml", top_k=1, max_chars=1200)

    assert snippets
    assert snippets[0]["references"]
    assert "scikit-learn" in " ".join(snippets[0]["references"])


def test_reference_section_is_metadata_not_retrieved_chunk():
    snippets = retrieve_knowledge("参考来源 scikit-learn PostgreSQL RFC", "ai_ml", top_k=5, max_chars=1200)

    assert all(item["title"] != "参考来源" for item in snippets)


def test_format_knowledge_for_prompt_includes_reference_field():
    snippets = retrieve_knowledge("TCP 三次握手 Wireshark 抓包", "computer_network", top_k=1, max_chars=1200)
    prompt_context = format_knowledge_for_prompt(snippets)

    assert "公开参考" in prompt_context
    assert "RFC" in prompt_context or "Wireshark" in prompt_context
