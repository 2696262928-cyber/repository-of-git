from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
SETTINGS_EXAMPLE = ROOT / "config" / "settings.example.json"
SETTINGS = ROOT / "config" / "settings.json"


def main() -> int:
    print("=" * 72)
    print("AI 实验报告助手 - 一键环境配置")
    print("=" * 72)
    print(f"项目目录：{ROOT}")

    if not REQUIREMENTS.exists():
        return fail("未找到 requirements.txt，请把本程序放在项目根目录运行。")

    python = find_python()
    if not python:
        return fail("未找到 Python。请先安装 Python 3.10+，并勾选 Add Python to PATH。")

    print(f"检测到 Python：{python}")
    run([python, "--version"])

    if not VENV_DIR.exists():
        print("\n[1/5] 创建虚拟环境 .venv ...")
        run([python, "-m", "venv", str(VENV_DIR)], check=True)
    else:
        print("\n[1/5] 已存在虚拟环境 .venv，跳过创建。")

    venv_python = VENV_DIR / "Scripts" / "python.exe"
    if not venv_python.exists():
        return fail("虚拟环境创建失败，未找到 .venv\\Scripts\\python.exe。")

    print("\n[2/5] 升级 pip ...")
    run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True)

    print("\n[3/5] 安装项目依赖，这一步可能需要几分钟 ...")
    run([str(venv_python), "-m", "pip", "install", "-r", str(REQUIREMENTS)], check=True)

    print("\n[4/5] 准备本地配置文件 ...")
    ensure_settings_file()

    print("\n[5/5] 验证关键依赖 ...")
    verify_imports(venv_python)

    print("\n环境配置完成。")
    print("\n启动方式：")
    print(r"  .\.venv\Scripts\streamlit.exe run app.py")
    print("\n如果要使用 DeepSeek 大模型评阅，请编辑：")
    print(r"  config\settings.json")
    print("把 api_key 改成你的真实 DeepSeek API Key。")
    print("\n按回车键退出。")
    input()
    return 0


def find_python() -> str | None:
    candidates = [
        shutil.which("python"),
        shutil.which("py"),
        sys.executable if not getattr(sys, "frozen", False) else None,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            result = subprocess.run(
                [candidate, "--version"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=10,
            )
            version_text = (result.stdout or result.stderr).strip()
            if result.returncode == 0 and "Python" in version_text:
                return candidate
        except Exception:
            continue
    return None


def ensure_settings_file() -> None:
    if SETTINGS.exists():
        print("config/settings.json 已存在，保留当前配置。")
        return
    if SETTINGS_EXAMPLE.exists():
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SETTINGS_EXAMPLE, SETTINGS)
        print("已从 settings.example.json 创建 config/settings.json。")
    else:
        print("未找到 settings.example.json，跳过配置文件创建。")


def verify_imports(venv_python: Path) -> None:
    code = (
        "import streamlit, fitz, docx, pandas, requests; "
        "from rapidocr_onnxruntime import RapidOCR; "
        "import cv2; "
        "import numpy; "
        "print('cv2 version:', cv2.__version__); "
        "print('关键依赖验证通过')"
    )
    run([str(venv_python), "-c", code], check=True)


def run(command: list[str], check: bool = False) -> subprocess.CompletedProcess:
    print("> " + " ".join(quote_if_needed(part) for part in command))
    result = subprocess.run(command, cwd=ROOT, text=True)
    if check and result.returncode != 0:
        print("\n命令执行失败，请查看上方错误信息。")
        print("按回车键退出。")
        input()
        raise SystemExit(result.returncode)
    return result


def quote_if_needed(value: str) -> str:
    return f'"{value}"' if " " in value else value


def fail(message: str) -> int:
    print("\n配置失败：" + message)
    print("按回车键退出。")
    input()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
