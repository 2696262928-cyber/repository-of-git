import json

import requests


def evaluate_with_openai_compatible_api(report_text: str, rubric: dict, settings: dict, prompt_template: str) -> dict:
    """Call an OpenAI-compatible chat completion API and return parsed JSON."""
    prompt = prompt_template.format(
        report_text=report_text,
        rubric=json.dumps(rubric, ensure_ascii=False, indent=2),
    )
    llm_settings = settings["llm"]
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
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)
