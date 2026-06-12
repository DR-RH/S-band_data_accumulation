#!/bin/zsh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REQUIRED_PYTHON="3.11"

find_python311() {
  local candidate
  for candidate in python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)' >/dev/null 2>&1; then
      BASE_PY="$candidate"
      return 0
    fi
  done
  return 1
}

if ! find_python311; then
  echo "[ERROR] Python $REQUIRED_PYTHON was not found."
  echo "Install Python $REQUIRED_PYTHON and make sure python3.11/python3/python is on PATH."
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

  echo "Checking venv Python version..."
  if ! "$venv_py" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)' >/dev/null 2>&1; then
    echo "[ERROR] $app/.venv is not Python $REQUIRED_PYTHON."
    "$venv_py" --version || true
    echo "Delete $app/.venv and run 00_setup_all.command again."
    exit 1
  fi

  echo "Upgrading pip/build tools..."
  "$venv_py" -m pip install --upgrade pip setuptools wheel

  echo "Installing requirements..."
  "$venv_py" -m pip install --prefer-binary -r "$req"
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
