import json
import os
from pathlib import Path


def load_settings(path: str = "config/settings.json") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        config_path = Path("config/settings.example.json")
    settings = json.loads(config_path.read_text(encoding="utf-8"))
    _apply_api_key_from_env(settings)
    return settings


def _apply_api_key_from_env(settings: dict) -> None:
    llm = settings.get("llm")
    if not isinstance(llm, dict):
        return

    current = llm.get("api_key", "")
    if current and current != "YOUR_API_KEY_HERE" and "API Key" not in current:
        return

    env_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if env_key:
        llm["api_key"] = env_key
