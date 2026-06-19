@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\streamlit.exe" (
  echo 未找到虚拟环境或 Streamlit，请先运行 setup_env.exe。
  pause
  exit /b 1
)
".venv\Scripts\streamlit.exe" run app.py
pause
