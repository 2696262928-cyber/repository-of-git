import json
from pathlib import Path


RUBRIC_DIR = Path("config/rubrics")


def list_rubrics() -> list[dict]:
    rubrics = []
    for path in sorted(RUBRIC_DIR.glob("*.json")):
        rubrics.append(load_rubric(path.stem))
    return rubrics


def load_rubric(course_type: str) -> dict:
    path = RUBRIC_DIR / f"{course_type}.json"
    if not path.exists():
        raise FileNotFoundError(f"Rubric not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
