# 知识库与 RAG 说明

## 1. 设计目标

本项目的知识库不是通用百科，而是面向“计算机类课程实验报告评阅”的本地参考资料。它的作用是给大模型提供更稳定的课程背景、评分关注点、常见扣分点和典型实验关键词，从而减少大模型只凭泛化经验评阅的问题。

当前知识库覆盖 7 类课程：

- 程序设计
- 数据结构与算法
- 数据库
- 操作系统
- 计算机网络
- 人工智能与机器学习
- 嵌入式系统

## 2. 文件结构

知识库位于：

```text
data/knowledge_base/
├── programming.md
├── data_structure.md
├── database.md
├── operating_system.md
├── computer_network.md
├── ai_ml.md
└── embedded_system.md
```

每个文件采用 Markdown 二级标题切块。检索模块会把每个 `##` 章节作为一个候选片段，并跳过 `## 参考来源`，将参考来源作为元数据附加到召回片段上。

## 3. 当前检索策略

位置：

```text
src/retriever/simple_retriever.py
```

当前实现为轻量 BM25：

1. 根据课程类型优先加权对应知识文件。
2. 对报告文本进行中文二/三字 gram 与英文 token 分词。
3. 对知识库章节进行 BM25 相关度打分。
4. 返回前 `top_k` 个片段。
5. 控制总上下文长度不超过 `max_chars`。
6. 将本地来源、匹配关键词、BM25 分数和公开参考资料展示在界面/导出报告中。

当前版本不使用 FAISS、Chroma、Milvus 等向量数据库，也不需要额外部署 embedding 模型。这样做的优点是运行简单、依赖少、适合课程大作业演示；不足是近义表达和跨语义召回能力弱于向量检索。

RAG 检索 query 由三部分组成：

```text
报告凝练文本 + 当前任务类型 + 用户需求
```

用户输入会直接影响召回重点。例如用户输入“重点检查 KNN 参数选择是否充分”，系统更容易召回 KNN、特征缩放、混淆矩阵、模型评估等片段；用户输入“事务实验设计是否充分”，系统会更偏向召回数据库事务、隔离级别、回滚验证和并发异常相关片段。

## 4. Prompt 使用方式

RAG 内容不会混入学生原始报告，而是作为独立字段传入 Prompt：

```text
本地课程知识库参考：
{knowledge_context}
```

Prompt 中明确约束：知识库只能作为课程背景和评分依据，不能把知识库中存在但学生报告中没有出现的内容当成学生已经完成的内容。

## 5. 参考资料来源

知识库内容参考公开课程资料和官方文档后改写，主要来源包括：

- Python Tutorial, Python Software Foundation: https://docs.python.org/3/tutorial/
- PEP 8 Style Guide for Python Code: https://peps.python.org/pep-0008/
- OpenDSA Data Structures and Algorithms: https://opendsa-server.cs.vt.edu/ODSA/Books/Everything/html/
- PostgreSQL Documentation: https://www.postgresql.org/docs/current/
- Operating Systems: Three Easy Pieces: https://pages.cs.wisc.edu/~remzi/OSTEP/
- Linux man-pages: https://man7.org/linux/man-pages/
- RFC 9293 Transmission Control Protocol: https://datatracker.ietf.org/doc/html/rfc9293
- RFC 768 User Datagram Protocol: https://datatracker.ietf.org/doc/html/rfc768
- RFC 9110 HTTP Semantics: https://www.rfc-editor.org/rfc/rfc9110.html
- Wireshark User's Guide: https://www.wireshark.org/docs/wsug_html_chunked/
- scikit-learn User Guide: https://scikit-learn.org/stable/user_guide.html
- FreeRTOS Documentation: https://www.freertos.org/Documentation/00-Overview
- Arm CMSIS NVIC Documentation: https://arm-software.github.io/CMSIS_5/Core/html/group__NVIC__gr.html

## 6. 维护建议

后续如果继续扩充知识库，建议遵循以下规则：

- 每个课程文件控制在 5-10 个二级标题，避免片段过碎。
- 每个片段既包含知识点，也包含“评阅时应检查什么”。
- 新增内容优先围绕具体实验类型，例如 KNN、事务隔离、三次握手、页面置换、循环队列。
- 参考来源放在文件末尾 `## 参考来源` 中，由检索模块自动作为元数据带出。
- 避免直接复制整段教材或文档，应该改写成项目所需的评分参考。

## 7. 当前局限

- 当前是轻量 BM25，不是向量数据库，语义近义词召回能力有限。
- 中文分词使用二/三字 gram，能覆盖常见关键词，但不如专业分词器精细。
- 所有课程共用同一检索策略，没有针对不同课程设置独立权重。
- 知识库主要服务实验报告评阅，不适合直接当成课程问答系统。

这些局限不影响课程大作业展示，反而可以在报告中作为“系统不足与改进方向”说明。
