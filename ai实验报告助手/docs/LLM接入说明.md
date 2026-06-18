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
3. 勾选“启用大模型评阅”。
4. 点击“开始检测”。

## 四、常见错误

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
