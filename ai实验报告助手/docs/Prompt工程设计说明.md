# Prompt 工程设计说明

## 1. 设计目标

本项目将大模型能力拆分为多个明确任务，而不是只使用一个通用聊天提示词。每类任务都定义独立的角色设定、输入变量、输出 JSON 格式和约束条件，使系统能够稳定生成可解析、可展示、可导出的结果。

## 2. 多任务 Prompt 设计表

| 任务模式 | Prompt 文件 | 角色设定 | 输出重点 |
| --- | --- | --- | --- |
| 全面评阅 | `prompts/report_review_prompt.txt` | 计算机专业课程实验报告智能评阅助手 | 总分、分项评分、问题建议、教师评语、风险提示 |
| 按需求重点检查 | `prompts/focused_review_prompt.txt` | 实验报告专项检查助手 | 针对用户关注点的结论 + 结构化评分 |
| 基于报告问答 | `prompts/report_qa_prompt.txt` | 实验报告问答助手 | 回答、依据、缺失信息、建议、引用来源 |
| 生成修改计划 | `prompts/revision_plan_prompt.txt` | 实验报告修改计划助手 | 高优先级修改、快速修复、深度改进、预计收益 |
| 生成教师评语 | `prompts/teacher_comment_prompt.txt` | 教师评语生成助手 | 评语草稿、优点、不足、建议分数 |

辅助 Prompt 文件：

- `prompts/course_classification_prompt.txt`：课程分类扩展预留，用于后续把规则分类升级为 LLM 辅助分类。
- `prompts/risk_check_prompt.txt`：风险检查扩展预留，用于后续把规则风险检测升级为 LLM 辅助诊断。

## 3. 输入变量设计

所有 Prompt 统一使用以下变量：

- `{report_text}`：上传报告经解析和凝练后的文本。
- `{rubric}`：当前课程对应的评分标准。
- `{diagnostics}`：规则预检、结构检测、图片分析等诊断信息。
- `{knowledge_context}`：BM25 RAG 召回的本地课程知识库片段。
- `{task_type}`：当前任务模式。
- `{user_instruction}`：用户输入的需求、问题或关注点。

## 4. 输出格式约束

所有任务要求模型输出合法 JSON，不允许额外添加 Markdown 代码块。系统会根据任务类型检查必要字段：

- 全面评阅/重点检查：必须包含 `summary`、`total_score`、`dimension_scores`、`problems`、`teacher_comment`、`risk_warnings`。
- 报告问答：必须包含 `answer`、`evidence`、`missing_info`、`suggestions`、`cited_sources`。
- 修改计划：必须包含 `summary`、`priority_actions`、`quick_fixes`、`deep_improvements`、`expected_score_gain`。
- 教师评语：必须包含 `teacher_comment`、`strengths`、`weaknesses`、`score_suggestion`。

系统在 `src/evaluator/llm_evaluator.py` 中通过 `TASK_DEFINITIONS` 映射任务类型、Prompt 文件和必要字段。模型返回后会先解析 JSON，再按任务类型校验字段；校验失败时页面会提示大模型结果格式异常，并保留规则检测兜底能力。

## 5. 约束条件

Prompt 中统一加入以下约束：

- 不能凭空编造报告中不存在的实验、代码、结果、图片或分析。
- 如果报告信息缺失，必须说明“报告中未提供”。
- 用户输入只能改变关注重点，不能覆盖评分标准。
- 本地知识库只能作为课程背景和评分依据，不能当作学生报告内容。
- 检测结果是辅助评阅建议，不能替代教师最终判断。

## 6. RAG 使用策略

系统保留现有 BM25 RAG，不接入向量数据库。RAG 检索 query 由三部分组成：

```text
报告凝练文本 + 当前任务类型 + 用户输入
```

这样可以让用户关注点影响知识库召回。例如用户输入“重点检查 KNN 参数选择是否充分”，系统更容易召回 KNN、特征缩放、混淆矩阵和模型评估相关片段。

## 7. Prompt 迭代优化记录

| 版本 | 发现的问题 | 优化方式 |
| --- | --- | --- |
| v1 | 单一 Prompt 只能做报告评分 | 增加多任务 Prompt 模板 |
| v2 | 模型输出不稳定 | 统一要求合法 JSON 输出 |
| v3 | 模型容易泛泛评价 | 增加 Rubric、预检诊断和问题定位要求 |
| v4 | RAG 内容可能被误当作学生内容 | 增加“知识库只作为参考”的边界约束 |
| v5 | 用户不能表达具体关注点 | 新增用户需求输入，并让其参与 Prompt 与 RAG 检索 |

## 8. 当前边界

- 当前是单轮任务式生成，不做多轮对话。
- 当前 RAG 使用轻量 BM25，不使用向量数据库。
- 当前不做模型训练或微调。
- 关闭大模型时，系统仍可回退到规则基础评阅，但问答、修改计划和教师评语任务需要大模型才能得到完整结果。
