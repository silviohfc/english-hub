@echo off
rem dev-english: starts the local server and opens the browser.
cd /d "%~dp0"
where uv >nul 2>nul || (echo uv nao encontrado. Instale com: winget install astral-sh.uv & pause & exit /b 1)
if not exist "models\kokoro-v1.0.onnx" (
  echo Baixando modelos pela primeira vez - ~2 GB...
  uv run python scripts\download_models.py || (pause & exit /b 1)
)
start "" "http://127.0.0.1:8765"
uv run python -m app.main
pause
