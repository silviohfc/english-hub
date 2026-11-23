@echo off
rem english-hub: starts the local server; the browser opens on the setup screen on first run.
cd /d "%~dp0"
where uv >nul 2>nul || (echo uv nao encontrado. Instale com: winget install astral-sh.uv & pause & exit /b 1)
if not exist ".venv" echo Instalando dependencias na primeira vez, pode levar alguns minutos...
uv run python -m app.main
pause
