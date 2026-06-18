import json
import re

import requests


class LLMEvaluationError(RuntimeError):
    pass


def evaluate_with_openai_compatible_api(report_text: str, rubric: dict, settings: dict, prompt_template: str) -> dict:
    """Call an OpenAI-compatible chat completion API and return parsed JSON."""
    _validate_settings(settings)
    prompt = (
        prompt_template
        .replace("{report_text}", report_text)
        .replace("{rubric}", json.dumps(rubric, ensure_ascii=False, indent=2))
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
                    {"role": "system", "content": "你是严谨的计算机专业实验报告评阅助手。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=90,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise LLMEvaluationError(f"API 请求失败：{exc}") from exc

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise LLMEvaluationError("API 返回格式不是兼容的 chat/completions 结构。") from exc

    review = _parse_json_content(content)
    _validate_review(review)
    return review


def _validate_settings(settings: dict) -> None:
    llm_settings = settings.get("llm", {})
    missing = [key for key in ["base_url", "api_key", "model"] if not llm_settings.get(key)]
    if missing:
        raise ValueError("缺少 LLM 配置项：" + "、".join(missing))
    if llm_settings["api_key"] == "YOUR_API_KEY_HERE":
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


def _validate_review(review: dict) -> None:
    required = ["summary", "total_score", "dimension_scores", "problems", "teacher_comment", "risk_warnings"]
    missing = [key for key in required if key not in review]
    if missing:
        raise LLMEvaluationError("模型评阅结果缺少字段：" + "、".join(missing))
