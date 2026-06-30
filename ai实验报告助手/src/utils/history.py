from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HISTORY_PATH = PROJECT_ROOT / "outputs" / "history.jsonl"


def append_history_record(record: dict, path: Path = DEFAULT_HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **record}
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_history(limit: int = 20, path: Path = DEFAULT_HISTORY_PATH) -> list[dict]:
    if limit <= 0 or not path.exists():
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    records = []
    for line in reversed(lines[-limit:]):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records

