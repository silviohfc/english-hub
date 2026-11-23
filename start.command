#!/bin/bash
# english-hub (macOS/Linux): starts the local server; the browser opens on the setup screen.
# On a Mac, double-click this file in Finder (or run ./start.command in a terminal).
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/share/mise/shims:$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

pause() { read -r -p "Pressione Enter para fechar..." _; }

if ! command -v uv >/dev/null 2>&1; then
  echo "uv nao encontrado. Instale com: mise use -g uv@latest  (ou: brew install uv)"
  echo "  ou: curl -LsSf https://astral.sh/uv/install.sh | sh"
  pause; exit 1
fi
if ! command -v claude >/dev/null 2>&1; then
  echo "Aviso: Claude Code CLI ('claude') nao encontrado no PATH."
fi

[ -d .venv ] || echo "Instalando dependencias na primeira vez, pode levar alguns minutos..."
# The server opens the browser itself (setup screen on first run).
uv run python -m app.main
pause
