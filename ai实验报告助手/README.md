# 面向计算机类课程的实验报告智能检测与反馈系统

本项目是《人工智能导论》期末大作业项目骨架，目标是实现一个面向计算机类课程实验报告的智能检测与反馈系统。系统支持上传实验报告，自动解析内容，识别课程类型，并结合评分规则与大语言模型输出结构化评分、问题定位、修改建议和教师评语。

## 项目定位

本系统不是代写实验报告，而是用于辅助学生自查和教师评阅。核心场景包括：

- 程序设计实验报告检测
- 数据结构与算法实验报告检测
- 数据库实验报告检测
- 操作系统实验报告检测
- 计算机网络实验报告检测
- 人工智能与机器学习实验报告检测

## 核心流程

```text
上传实验报告
-> 解析报告文本、表格和代码片段
-> 识别课程/实验类型
-> 匹配课程评分 Rubric
-> 调用大语言模型分析
-> 输出评分、问题、建议和教师评语
-> 导出检测报告
```

## 技术栈建议

- 前端界面：Streamlit
- 后端语言：Python
- 文档解析：python-docx、PyMuPDF
- 大模型接入：DeepSeek / Qwen / OpenAI-compatible API / Ollama
- 评分规则：JSON Rubric
- 检测结果导出：Markdown，后续可扩展 DOCX / PDF

## 目录结构

```text
.
├─ app.py                         # Streamlit 主入口
├─ requirements.txt               # Python 依赖
├─ config/
│  ├─ settings.example.json        # 配置示例
│  └─ rubrics/                     # 课程评分规则
├─ data/
│  ├─ knowledge_base/              # 课程资料、报告模板、常见问题
│  └─ samples/                     # 测试样例
├─ docs/
│  ├─ 项目设计说明.md
│  ├─ 成员分工.md
│  └─ 测试用例.md
├─ prompts/                        # 大模型 Prompt 模板
├─ outputs/                        # 检测结果导出目录
├─ src/
│  ├─ classifier/                  # 课程类型识别
│  ├─ evaluator/                   # 评分与 LLM 检测
│  ├─ exporter/                    # 结果导出
│  ├─ parser/                      # 报告解析
│  └─ utils/                       # 通用工具
└─ tests/                          # 测试代码
```

## 快速开始

1. 创建并激活 Python 虚拟环境。

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. 安装依赖。

```bash
pip install -r requirements.txt
```

3. 复制配置文件。

```bash
copy config\settings.example.json config\settings.json
```

4. 修改 `config/settings.json` 中的模型 API 配置。

5. 启动系统。

```bash
streamlit run app.py
```

## 最小可交付功能

- 上传 DOCX / PDF / TXT / Markdown 实验报告
- 提取报告正文
- 手动选择或自动识别课程类型
- 读取对应课程评分 Rubric
- 调用 LLM 输出评分和反馈
- 页面展示检测结果
- 导出 Markdown 检测报告

## 协作建议

建议使用以下分支：

- `main`：稳定版本
- `dev`：开发整合版本
- `feature/parser`：文档解析
- `feature/frontend`：页面界面
- `feature/llm`：模型接入
- `feature/rubric`：评分规则
- `feature/export`：检测报告导出

提交信息示例：

```text
feat: add docx parser
feat: add rubric loader
fix: handle empty pdf content
docs: update test cases
```

## 注意事项

- 不要提交真实 API Key。
- 不要提交包含隐私信息的学生报告。
- 外部 API 使用情况需要在最终报告中声明。
- 检测结果应表述为辅助评阅建议，不应声称能够绝对判定抄袭或 AI 生成。
