import json
import re
from pathlib import Path

import requests


class LLMEvaluationError(RuntimeError):
    pass


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_DIR = PROJECT_ROOT / "prompts"

REVIEW_REQUIRED_FIELDS = [
    "summary",
    "total_score",
    "dimension_scores",
    "problems",
    "teacher_comment",
    "risk_warnings",
]

TASK_DEFINITIONS = {
    "report_review": {
        "label": "全面评阅",
        "prompt_file": "report_review_prompt.txt",
        "required_fields": REVIEW_REQUIRED_FIELDS,
        "requires_instruction": False,
    },
    "focused_review": {
        "label": "按需求重点检查",
        "prompt_file": "focused_review_prompt.txt",
        "required_fields": REVIEW_REQUIRED_FIELDS + ["focused_conclusion"],
        "requires_instruction": True,
    },
    "report_qa": {
        "label": "基于报告问答",
        "prompt_file": "report_qa_prompt.txt",
        "required_fields": ["answer", "evidence", "missing_info", "suggestions", "cited_sources"],
        "requires_instruction": True,
    },
    "revision_plan": {
        "label": "生成修改计划",
        "prompt_file": "revision_plan_prompt.txt",
        "required_fields": ["summary", "priority_actions", "quick_fixes", "deep_improvements", "expected_score_gain"],
        "requires_instruction": False,
    },
    "teacher_comment": {
        "label": "生成教师评语",
        "prompt_file": "teacher_comment_prompt.txt",
        "required_fields": ["teacher_comment", "strengths", "weaknesses", "score_suggestion"],
        "requires_instruction": False,
    },
}


def evaluate_with_openai_compatible_api(
    report_text: str,
    rubric: dict,
    settings: dict,
    prompt_template: str,
    diagnostics: dict | None = None,
    knowledge_context: str = "",
) -> dict:
    """Backward-compatible wrapper for the default full review task."""
    return evaluate_task_with_openai_compatible_api(
        report_text,
        rubric,
        settings,
        prompt_template,
        diagnostics=diagnostics,
        knowledge_context=knowledge_context,
        task_type="report_review",
        user_instruction="",
    )


def evaluate_task_with_openai_compatible_api(
    report_text: str,
    rubric: dict,
    settings: dict,
    prompt_template: str,
    diagnostics: dict | None = None,
    knowledge_context: str = "",
    task_type: str = "report_review",
    user_instruction: str = "",
) -> dict:
    """Call an OpenAI-compatible chat completion API and return parsed JSON."""
    _validate_settings(settings)
    task = get_task_definition(task_type)
    if task["requires_instruction"] and not user_instruction.strip():
        raise ValueError(f"{task['label']}需要填写用户需求/问题。")

    prompt = build_prompt(
        prompt_template,
        report_text=report_text,
        rubric=rubric,
        diagnostics=diagnostics,
        knowledge_context=knowledge_context,
        task_type=task_type,
        user_instruction=user_instruction,
    )
    llm_settings = settings["llm"]
    try:
        response = requests.post(
            f"{llm_settings['base_url'].rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {llm_settings['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": llm_settings["model"],
                "messages": [
                    {"role": "system", "content": f"你是严谨的计算机专业实验报告分析助手，当前任务是：{task['label']}。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=(30, 300),  # (connect_timeout, read_timeout) 连接30s，读取300s
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise LLMEvaluationError(f"API 请求失败：{exc}") from exc

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise LLMEvaluationError("API 返回格式不是兼容的 chat/completions 结构。") from exc

    result = _parse_json_content(content)
    validate_task_result(result, task_type)
    return result


def get_task_definition(task_type: str) -> dict:
    if task_type not in TASK_DEFINITIONS:
        raise ValueError(f"未知任务类型：{task_type}")
    return TASK_DEFINITIONS[task_type]


def get_prompt_template_path(task_type: str) -> Path:
    task = get_task_definition(task_type)
    return PROMPT_DIR / task["prompt_file"]


def load_prompt_template(task_type: str) -> str:
    return get_prompt_template_path(task_type).read_text(encoding="utf-8")


def build_prompt(
    prompt_template: str,
    *,
    report_text: str,
    rubric: dict,
    diagnostics: dict | None = None,
    knowledge_context: str = "",
    task_type: str = "report_review",
    user_instruction: str = "",
) -> str:
    task = get_task_definition(task_type)
    replacements = {
        "{report_text}": report_text,
        "{rubric}": json.dumps(rubric, ensure_ascii=False, indent=2),
        "{diagnostics}": json.dumps(diagnostics or {}, ensure_ascii=False, indent=2),
        "{knowledge_context}": knowledge_context or "未启用或未检索到本地课程知识库参考。",
        "{task_type}": task["label"],
        "{user_instruction}": user_instruction.strip() or "用户未提供额外需求。",
    }
    prompt = prompt_template
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)
    return prompt


def build_task_rag_query(report_text: str, task_type: str, user_instruction: str = "") -> str:
    task = get_task_definition(task_type)
    return "\n\n".join(
        [
            report_text,
            f"任务类型：{task['label']}",
            f"用户需求：{user_instruction.strip()}" if user_instruction.strip() else "用户未提供额外需求。",
        ]
    )


def validate_task_result(result: dict, task_type: str) -> None:
    task = get_task_definition(task_type)
    missing = [key for key in task["required_fields"] if key not in result]
    if missing:
        raise LLMEvaluationError("模型任务结果缺少字段：" + "、".join(missing))


def _validate_settings(settings: dict) -> None:
    llm_settings = settings.get("llm", {})
    missing = [key for key in ["base_url", "api_key", "model"] if not llm_settings.get(key)]
    if missing:
        raise ValueError("缺少 LLM 配置项：" + "、".join(missing))
    if llm_settings["api_key"] == "YOUR_API_KEY_HERE" or "API Key" in llm_settings["api_key"]:
        raise ValueError("请先在 config/settings.json 中填写真实 API Key。")


def _parse_json_content(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            raise LLMEvaluationError("模型没有返回 JSON 内容。")
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LLMEvaluationError("模型返回了 JSON 片段，但格式无法解析。") from exc
