# 面向计算机类课程的实验报告智能检测与反馈系统

上传实验报告 → 选择任务模式并输入需求 → 自动解析文档、智能凝练文本、识别图片内容 → BM25 RAG 召回课程知识 → 大模型生成评分/问答/修改计划/教师评语 → 导出报告并保存学习反馈。

---

## 朋友拉取后如何运行

### 前提：电脑已安装 Python 3.10+

没有的话去 https://www.python.org/downloads/ 下载，安装时勾选 **Add Python to PATH**。

### 推荐启动方式

方式一：双击启动脚本。

```text
start_app.bat
```

方式二：命令行启动。

```bash
# 1. 进入项目目录
cd ai实验报告助手

# 2. 一键配置环境（自动创建虚拟环境、安装所有依赖）
python setup_env.py

# 3. 启动系统
.venv\Scripts\streamlit.exe run app.py
```

浏览器会自动打开 `http://localhost:8501`。

方式三：本地开发启动。若已经配置了本地环境变量或个人 API Key，可使用：

```text
start_app_local.bat
```

该文件只用于本机开发，已被 `.gitignore` 排除，不应提交。

> 如果第 2 步报错，也可以手动执行：
> ```bash
> python -m venv .venv
> .venv\Scripts\python.exe -m pip install -r requirements.txt
> copy config\settings.example.json config\settings.json
> ```

### 使用大模型评阅

编辑 `config\settings.json`，把 `api_key` 改成你的 DeepSeek API Key：

```json
{
  "llm": {
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "你的真实API Key",
    "model": "deepseek-chat"
  }
}
```

不填 API Key 也能用，系统会用规则引擎给出基础评分。

---

## 功能概览

| 模块 | 能力 |
|------|------|
| 文档解析 | 支持 DOCX / PDF / TXT / Markdown，提取文本、表格、代码块 |
| 智能凝练 | 保留章节/代码/技术参数，压缩描述性文字，减少 LLM 调用时间 |
| 图片分析 | OpenCV 分类图片类型（波形图/表格/代码截图/电路图），评估质量 |
| 图片内容提取 | 表格 OCR、波形信号检测、代码截图逐行识别 |
| 图片位置关联 | 每张图片标注所在页码和章节，交叉验证图片类型与位置是否匹配 |
| 进度可视化 | 上传后展示实时分析流水线（文档解析→文本凝练→图片分析→位置关联→融合） |
| 课程识别 | 自动识别程序设计/数据结构/数据库/操作系统/计网/AI/嵌入式等课程 |
| 本地知识库增强 | 使用轻量 BM25 检索，根据课程类型和报告关键词召回本地课程知识片段，并附带本地来源、匹配关键词和公开参考资料 |
| 多任务 Prompt | 支持全面评阅、按需求重点检查、基于报告问答、生成修改计划、生成教师评语 |
| 用户需求输入 | 上传报告后可输入自己的问题或关注点，参与 RAG 检索和大模型 Prompt |
| LLM 生成 | 调用 DeepSeek API 输出评分、问答、修改计划或教师评语等结构化结果 |
| 结果导出 | 下载 Markdown / Word DOCX 格式检测报告 |
| 历史记录 | 自动保存检测摘要，便于查看最近检测文件、分数、问题数量和是否启用 LLM/RAG |
| 用户反馈 / 学习记录 | 检测后记录反馈是否有帮助、是否准备采纳、主要薄弱点和后续修改计划 |

---

## 典型使用流程

1. 在左侧上传 DOCX / PDF / TXT / Markdown 实验报告。
2. 选择课程类型，或保持“自动识别”。
3. 在主页面“第二步：选择任务与输入需求”中选择任务模式。
4. 按需要填写“我的需求 / 问题 / 关注点”。
5. 在左侧勾选“启用大模型评阅”和“启用本地知识库 RAG”。
6. 点击“开始检测”。
7. 查看解析预览、RAG 引用、检测结果和原始 JSON。
8. 下载 Markdown / Word DOCX 检测报告。
9. 在“用户反馈 / 学习记录”中保存帮助度、采纳状态、薄弱点和后续修改计划。

---

## 知识库与 RAG

本地知识库位于 `data/knowledge_base/`，覆盖程序设计、数据结构、数据库、操作系统、计算机网络、人工智能与机器学习、嵌入式系统 7 类课程。每个知识文件按 Markdown 二级标题切块，RAG 模块会召回最相关片段，并在界面、Prompt 和导出报告中显示引用来源。

详细说明见：`docs/知识库与RAG说明.md`。

## Prompt 工程

系统将大模型能力拆分为 5 类任务：全面评阅、按需求重点检查、基于报告问答、生成修改计划和生成教师评语。每类任务都有独立 Prompt 模板，明确角色设定、输入变量、输出 JSON 结构、约束条件和 RAG 使用边界。

详细说明见：`docs/Prompt工程设计说明.md`。

---

## 配套文档

| 文档 | 用途 |
| --- | --- |
| `docs/用户使用说明.md` | 给老师、队友和普通用户看的操作手册 |
| `docs/项目设计说明.md` | 系统背景、架构、模块和技术路线 |
| `docs/Prompt工程设计说明.md` | 多任务 Prompt、JSON 输出约束和迭代记录 |
| `docs/知识库与RAG说明.md` | 本地知识库、BM25 检索和来源引用说明 |
| `docs/LLM接入说明.md` | DeepSeek/OpenAI-compatible API 配置方法 |
| `docs/测试用例.md` | 样例文件和推荐测试组合 |
| `docs/测试结果记录.md` | 自动测试、样例验证和待人工验证表 |
| `docs/手动测试记录.md` | 最终提交前填写的真实前端测试记录 |
| `docs/演示视频脚本.md` | 5-8 分钟演示视频顺序和话术 |
| `docs/报告撰写交接.md` | 给下一个写最终报告同学的交接摘要 |

---

## 目录结构

```text
.
├── app.py                           # Streamlit 主入口
├── requirements.txt                 # Python 依赖
├── setup_env.py                     # 一键环境配置脚本
├── start_app.bat                    # 双击启动
├── config/
│   ├── settings.example.json        # 配置模板
│   ├── settings.json                # 本地配置（含 API Key，已在 .gitignore）
│   └── rubrics/                     # 课程评分规则 JSON
├── prompts/
│   ├── report_review_prompt.txt     # 全面评阅 Prompt
│   ├── focused_review_prompt.txt    # 按需求重点检查 Prompt
│   ├── report_qa_prompt.txt         # 基于报告问答 Prompt
│   ├── revision_plan_prompt.txt     # 修改计划 Prompt
│   ├── teacher_comment_prompt.txt   # 教师评语 Prompt
│   ├── course_classification_prompt.txt # 课程分类辅助 Prompt
│   └── risk_check_prompt.txt        # 风险检查辅助 Prompt
├── data/
│   ├── samples/                     # 测试样例
│   └── knowledge_base/              # 本地课程知识库（轻量 RAG）
├── src/
│   ├── analyzer/                    # 分析流水线（文本凝练、并行管道、融合）
│   ├── classifier/                  # 课程类型识别
│   ├── evaluator/                   # 评分、LLM 调用、报告诊断
│   ├── exporter/                    # 结果导出
│   ├── parser/                      # 文档解析、OCR、图片上下文提取
│   ├── retriever/                   # 本地知识库 BM25 检索
│   ├── vision/                      # OpenCV 图像处理与内容提取
│   └── utils/                       # 配置、历史记录、反馈记录
├── tests/                           # 自动测试
└── outputs/                         # 运行输出目录（历史记录/反馈记录，本地忽略不提交）
```

---

## 注意事项

- **不要提交 `config/settings.json`**（已在 .gitignore 中排除），里面包含 API Key
- **不要提交 `start_app_local.bat`、`.venv`、`outputs/*`**，这些都是本地环境或运行输出
- 不要提交含隐私信息的学生报告
- 检测结果为辅助评阅建议，不声称能绝对判定抄袭或 AI 生成
- 最终提交前请运行 `.\.venv\Scripts\python.exe -m pytest -q`，确认自动测试通过
