# 面向计算机类课程的实验报告智能检测与反馈系统

上传实验报告 → 自动解析文档、智能凝练文本、识别图片内容（波形图/表格/代码截图）→ 大模型评阅 → 输出评分、问题和修改建议。

---

## 朋友拉取后如何运行

### 前提：电脑已安装 Python 3.10+

没有的话去 https://www.python.org/downloads/ 下载，安装时勾选 **Add Python to PATH**。

### 三步启动

```bash
# 1. 进入项目目录
cd ai实验报告助手

# 2. 一键配置环境（自动创建虚拟环境、安装所有依赖）
python setup_env.py

# 3. 启动系统
.venv\Scripts\streamlit.exe run app.py
```

浏览器会自动打开 `http://localhost:8501`。

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
| LLM 评阅 | 调用 DeepSeek API 输出分项评分、问题定位、修改建议、教师评语 |
| 结果导出 | 下载 Markdown 格式检测报告 |

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
│   └── report_review_prompt.txt     # LLM 评阅 Prompt
├── data/
│   └── samples/                     # 测试样例
├── src/
│   ├── analyzer/                    # 分析流水线（文本凝练、并行管道、融合）
│   ├── classifier/                  # 课程类型识别
│   ├── evaluator/                   # 评分、LLM 调用、报告诊断
│   ├── exporter/                    # 结果导出
│   ├── parser/                      # 文档解析、OCR、图片上下文提取
│   ├── vision/                      # OpenCV 图像处理与内容提取
│   └── utils/                       # 配置加载
└── outputs/                         # 导出目录
```

---

## 注意事项

- **不要提交 `config/settings.json`**（已在 .gitignore 中排除），里面包含 API Key
- 不要提交含隐私信息的学生报告
- 检测结果为辅助评阅建议，不声称能绝对判定抄袭或 AI 生成
