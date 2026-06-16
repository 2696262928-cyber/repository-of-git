import json
from pathlib import Path


def load_settings(path: str = "config/settings.json") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        config_path = Path("config/settings.example.json")
    return json.loads(config_path.read_text(encoding="utf-8"))
