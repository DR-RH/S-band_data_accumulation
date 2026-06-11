#!/bin/zsh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
  BASE_PY="python3"
elif command -v python >/dev/null 2>&1; then
  BASE_PY="python"
else
  echo "[ERROR] Python was not found."
  echo "Install Python 3.11 or make sure python3/python is on PATH."
  read -r "?Press Enter to close..."
  exit 1
fi

setup_env() {
  local app="$1"
  local app_dir="$ROOT/$app"
  local venv_py="$app_dir/.venv/bin/python"
  local req="$app_dir/requirements.txt"

  echo "------------------------------------------------------------"
  echo "[$app]"

  if [[ ! -d "$app_dir" ]]; then
    echo "[ERROR] Folder not found: $app_dir"
    exit 1
  fi

  if [[ ! -f "$req" ]]; then
    echo "[ERROR] requirements.txt not found: $req"
    exit 1
  fi

  if [[ ! -x "$venv_py" ]]; then
    echo "Creating venv..."
    (cd "$app_dir" && "$BASE_PY" -m venv .venv)
  else
    echo "venv already exists."
  fi

  echo "Installing requirements..."
  "$venv_py" -m pip install -r "$req"
  echo "[OK] $app"
}

echo "Initial setup for S-band tools"
echo "Root: $ROOT"
echo "Python:"
"$BASE_PY" --version
echo

setup_env processor
setup_env server
setup_env downloader
setup_env decoder_core

echo
echo "[OK] Setup completed."
echo "Next steps:"
echo "  1. Put TLM .txt files into the TLM input alias."
echo "  2. Run 01_start_server.command."
echo "  3. Run 02_run_processor.command."
echo "  4. Open downloader/index.html or run 03_open_viewer.command."
read -r "?Press Enter to close..."

