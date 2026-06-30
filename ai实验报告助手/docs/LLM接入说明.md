# LLM 接入说明

本项目使用 OpenAI-compatible Chat Completions 接口接入大语言模型。DeepSeek、Qwen、硅基流动、Ollama OpenAI 兼容服务等都可以按此方式配置。

## 一、创建本地配置文件

在项目根目录执行：

```powershell
copy config\settings.example.json config\settings.json
```

`config/settings.json` 已经加入 `.gitignore`，不会被提交到 Git，适合保存个人 API Key。

## 二、填写 API 配置

打开 `config/settings.json`，修改 `llm` 部分：

```json
{
  "llm": {
    "provider": "openai_compatible",
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "在这里填写你的 API Key",
    "model": "deepseek-chat"
  },
  "app": {
    "default_course_type": "auto",
    "max_report_chars": 20000,
    "output_dir": "outputs"
  }
}
```

如果不希望把 API Key 写入文件，也可以只在 `config/settings.json` 中保留 `base_url` 和 `model`，然后在启动前设置环境变量：

```powershell
$env:DEEPSEEK_API_KEY="你的 API Key"
.\.venv\Scripts\streamlit.exe run app.py
```

程序会优先使用 `config/settings.json` 中的非占位 Key；如果仍是 `YOUR_API_KEY_HERE`，则自动读取 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`。

常见配置示例：

| 平台 | base_url 示例 | model 示例 |
| --- | --- | --- |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 硅基流动 | `https://api.siliconflow.cn/v1` | 按平台模型名填写 |
| 通义千问兼容接口 | 按平台文档填写 | 按平台模型名填写 |
| Ollama 本地兼容接口 | `http://localhost:11434/v1` | 本地模型名 |

## 三、页面中启用

启动项目：

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

在页面左侧：

1. 上传实验报告。
2. 选择课程类型或保持自动识别。
3. 在主页面选择任务模式，并按需要填写“我的需求 / 问题 / 关注点”。
4. 勾选“启用大模型评阅”；如需课程知识依据，可同时勾选“启用本地知识库 RAG”。
5. 点击“开始检测”。

## 四、多任务 Prompt 调用说明

当前所有大模型任务都走同一个 OpenAI-compatible Chat Completions 接口，但会根据任务模式选择不同 Prompt 模板：

| 任务模式 | Prompt 文件 | 说明 |
| --- | --- | --- |
| 全面评阅 | `prompts/report_review_prompt.txt` | 生成总分、分项评分、问题建议和教师评语 |
| 按需求重点检查 | `prompts/focused_review_prompt.txt` | 围绕用户输入的关注点重点检查 |
| 基于报告问答 | `prompts/report_qa_prompt.txt` | 基于报告内容和 RAG 片段回答用户问题 |
| 生成修改计划 | `prompts/revision_plan_prompt.txt` | 输出按优先级排列的修改清单 |
| 生成教师评语 | `prompts/teacher_comment_prompt.txt` | 生成适合教师批改场景的评语草稿 |

用户输入会同时进入 Prompt 和 RAG 检索 query。系统要求模型返回合法 JSON，并根据不同任务校验必要字段。非全面评阅任务依赖大模型生成；如果关闭大模型，系统只能输出规则检测的基础评分，不能完整生成问答、修改计划或教师评语。

API Key 只应保存在本地 `config/settings.json` 或环境变量中，不要写入代码、文档、截图或提交记录。

## 五、常见错误

### 1. 缺少 API Key

说明还没有创建或填写 `config/settings.json`。

### 2. 401 / 403

通常是 API Key 错误、余额不足或模型权限不足。

### 3. 404

通常是 `base_url` 或 `model` 填错。

### 4. 模型没有返回 JSON

说明模型没有严格遵守 Prompt。可以重试，或降低温度，或换成指令遵循能力更好的模型。

### 5. 请求超时

可能是网络较慢、报告文本太长或模型响应较慢。可以调小 `max_report_chars`。
